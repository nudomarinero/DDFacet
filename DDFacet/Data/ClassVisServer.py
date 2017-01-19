'''
DDFacet, a facet-based radio imaging package
Copyright (C) 2013-2016  Cyril Tasse, l'Observatoire de Paris,
SKA South Africa, Rhodes University

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
'''

import numpy as np
import math
import ClassMS
from DDFacet.Data.ClassStokes import ClassStokes
from DDFacet.Array import NpShared
from DDFacet.Other import ClassTimeIt
from DDFacet.Other import ModColor
from DDFacet.Array import ModLinAlg
from DDFacet.Other import MyLogger
from functools import reduce
MyLogger.setSilent(["NpShared"])
from DDFacet.Imager import ClassWeighting
from DDFacet.Other import reformat
import ClassSmearMapping
import os
import psutil
import ClassJones
import ClassBeamMean
from DDFacet.Other import Multiprocessing
from DDFacet.Array.SharedDict import SharedDict
log = MyLogger.getLogger("ClassVisServer")


def test():
    MSName = "/media/tasse/data/killMS_Pack/killMS2/Test/0000.MS"
    VS = ClassVisServer(MSName, TVisSizeMin=1e8, Weighting="Natural")
    VS.CalcWeights((1, 1, 1000, 1000), 20.*np.pi/180)
    VS.LoadNextVisChunk()


class ClassVisServer():

    def __init__(self, MSList, GD=None,
                 ColName="DATA",
                 TChunkSize=1,                # chunk size, in hours
                 LofarBeam=None,
                 AddNoiseJy=None,
                 APP=None, APP_id="VS"):   # AsyncProcessPool to use, if any
        self.GD = GD
        self.APP = APP
        if APP is not None:
            APP.registerEvents("VisWeights")
            APP.registerJobHandlers(**{APP_id:self})

        self.MSList = [ MSList ] if isinstance(MSList, str) else MSList
        self.FacetMachine = None
        self.AddNoiseJy = AddNoiseJy
        self.TMemChunkSize = TChunkSize

        self.Weighting = GD["Image"]["Weighting"].lower()
        if self.Weighting not in ("natural", "uniform", "briggs", "robust"):
            raise ValueError("unknown Weighting=%s" % Weighting)
        self.MFSWeighting = GD["Image"]["MFSWeighting"]
        self.Robust = GD["Image"]["Robust"]
        self.Super = GD["Image"]["SuperUniform"]
        self.VisWeights = None

        self.CountPickle = 0
        self.ColName = ColName
        self.DicoSelectOptions = GD["Selection"]
        self.TaQL = self.DicoSelectOptions.get("TaQL", None)
        self.LofarBeam = LofarBeam
        self.ApplyBeam = False
        self.datashape = None
        self._use_data_cache = self.GD["Cache"]["VisData"]
        self.Init()

        # buffers to hold current chunk
        self._databuf = None
        self._flagbuf = None

    def Init(self, PointingID=0):
        self.ListMS = []
        global_freqs = set()
        NChanMax = 0
        ChanStart = self.DicoSelectOptions.get("ChanStart", 0)
        ChanEnd = self.DicoSelectOptions.get("ChanEnd", -1)
        ChanStep = self.DicoSelectOptions.get("ChanStep", 1)
        if (ChanStart, ChanEnd, ChanStep) == (0, -1, 1):
            chanslice = None
        else:
            chanslice = slice(
                ChanStart,
                ChanEnd if ChanEnd != -
                1 else None,
                ChanStep)

        min_freq = 1e+999
        max_freq = 0

        # max chunk shape accumulated here
        self._chunk_shape = [0, 0, 0]

        for msspec in self.MSList:
            if type(msspec) is not str:
                msname, ddid, field = msspec
            else:
                msname, ddid, field = msspec, self.DicoSelectOptions["DDID"], self.DicoSelectOptions["Field"]
            MS = ClassMS.ClassMS(
                msname, Col=self.ColName, DoReadData=False,
                AverageTimeFreq=(1, 3),
                Field=field, DDID=ddid, TaQL=self.TaQL,
                TimeChunkSize=self.TMemChunkSize, ChanSlice=chanslice,
                GD=self.GD, ResetCache=self.GD["Cache"]["Reset"],
                DicoSelectOptions = self.DicoSelectOptions)
            self.ListMS.append(MS)
            # accumulate global set of frequencies, and min/max frequency
            global_freqs.update(MS.ChanFreq)
            min_freq = min(min_freq, (MS.ChanFreq-MS.ChanWidth/2).min())
            max_freq = max(max_freq, (MS.ChanFreq+MS.ChanWidth/2).max())
            # accumulate largest chunk shape
            for row0, row1 in MS.getChunkRow0Row1():
                shape = (row1-row0, len(MS.ChanFreq), MS.Ncorr)
                self._chunk_shape = [max(a, b)
                                     for a, b in zip(self._chunk_shape, shape)]

        size = reduce(lambda x, y: x * y, self._chunk_shape)
        print >>log, "shape of data/flag buffer will be %s (%.2f Gel)" % (
            self._chunk_shape, size / float(2 ** 30))

        if not self.ListMS:
            print>>log, ModColor.Str("--Data-MS does not specify any valid Measurement Set(s)")
            raise RuntimeError,"--Data-MS does not specify any valid Measurement Set(s)"

        # main cache is initialized from main cache of first MS
        self.maincache = self.cache = self.ListMS[0].maincache

        # Assume the correlation layout of the first measurement set for now
        self.VisCorrelationLayout = self.ListMS[0].CorrelationIds
        self.StokesConverter = ClassStokes(
            self.VisCorrelationLayout,
            self.GD["Image"]["PolMode"])
        for MS in self.ListMS:
            if not np.all(MS.CorrelationIds == self.VisCorrelationLayout):
                raise RuntimeError(
                    "Unsupported: Mixing Measurement Sets storing different correlation pairs are not supported at the moment")
                # TODO: it may be nice to have conversion code to deal with this

        self.nMS = len(self.ListMS)
        # make list of unique frequencies
        self.GlobalFreqs = np.array(sorted(global_freqs))
        self.CurrentMS = self.ListMS[0]
        self.iCurrentMS = 0

        bandwidth = max_freq - min_freq
        print>>log, "Total bandwidth is %g MHz (%g to %g MHz), with %d channels" % (
            bandwidth*1e-6, min_freq*1e-6, max_freq*1e-6, len(global_freqs))

        # print>>log,"GlobalFreqs: %d: %s"%(len(self.GlobalFreqs),repr(self.GlobalFreqs))

        # OMS: ok couldn't resist adding a bandwidth option since I need it for 3C147
        # if this is 0, then looks at NFreqBands parameter
        grid_bw = self.GD["Freq"]["BandMHz"]*1e+6

        if grid_bw:
            grid_bw = min(grid_bw, bandwidth)
            NFreqBands = self.GD["Freq"][
                "NBand"] = int(math.ceil(bandwidth/grid_bw))
        else:
            NFreqBands = np.min(
                [self.GD["Freq"]["NBand"],
                 len(self.GlobalFreqs)])  # self.nMS])
            grid_bw = bandwidth/NFreqBands

        self.NFreqBands = NFreqBands
        self.MultiFreqMode = NFreqBands > 1
        if self.MultiFreqMode:
            print>>log, ModColor.Str(
                "MultiFrequency Mode: ON, %dx%g MHz bands" %
                (NFreqBands, grid_bw*1e-6))

            if not ("Alpha" in self.GD["GAClean"]["GASolvePars"]):
                self.GD["GAClean"]["GASolvePars"].append("Alpha")

        else:
            self.GD["Freq"]["NBand"] = 1
            self.GD["HMP"]["Alpha"] = [0., 0., 1.]
            if "Alpha" in self.GD["GAClean"]["GASolvePars"]:
                self.GD["GAClean"]["GASolvePars"].remove("Alpha")
            print>>log, ModColor.Str("MultiFrequency Mode: OFF")

        # Divide the global frequencies into frequency bands.
        # Somewhat of an open question how best to do it (equal bandwidth, or equal number of channels?), this is where
        # we can play various games with mapping the GlobalFreqs into a number of image bands.
        # For now, let's do it by equal bandwith as Cyril used to do:

        # these aren't used anywhere except the loop to construct the mapping below, so I'll remove them
        # FreqBands = np.linspace(self.GlobalFreqs.min(),self.GlobalFreqs.max(),NFreqBands+1)
        # self.FreqBandsMin = FreqBands[0:-1].copy()
        # self.FreqBandsMax = FreqBands[1::].copy()
        # self.FreqBandsMean = (self.FreqBandsMin + self.FreqBandsMax)/2

        # grid_band: array of ints, same size as self.GlobalFreqs, giving the
        # grid band number of each frequency channel
        grid_band = np.floor((self.GlobalFreqs - min_freq)/grid_bw).astype(int)
        # freq_to_grid_band: mapping from frequency to grid band number
        freq_to_grid_band = dict(zip(self.GlobalFreqs, grid_band))
        # print>>log,sorted(freq_to_grid_band.items())

        self.FreqBandCenters = np.arange(
            min_freq+grid_bw/2, max_freq+grid_bw/2, grid_bw)
        self.FreqBandChannels = []
        # freq_to_grid_band_chan: mapping from frequency to channel number
        # within its grid band
        freq_to_grid_band_chan = {}
        for iBand in xrange(self.NFreqBands):
            freqlist = sorted([freq for freq, band
                               in freq_to_grid_band.iteritems()
                               if band == iBand])
            self.FreqBandChannels.append(freqlist)
            freq_to_grid_band_chan.update(
                dict([(freq, chan) for chan, freq in enumerate(freqlist)]))
            print>>log, "Image band %d: %g to %g MHz contains %d MS channels from %g to %g MHz" % (iBand, (self.FreqBandCenters[iBand]-grid_bw/2)*1e-6, (
                self.FreqBandCenters[iBand]+grid_bw/2)*1e-6, len(freqlist), len(freqlist) and freqlist[0]*1e-6, len(freqlist) and freqlist[-1]*1e-6)

        self.FreqBandChannelsDegrid = {}
        self.DicoMSChanMapping = {}
        self.DicoMSChanMappingChan = {}
        self.DicoMSChanMappingDegridding = {}
        # When gridding, we make a dirty/residual image with N=NFreqBands output bands
        # When degridding, we make a model with M channels (M may depend on MS).
        # The structures initialized here map between MS channels and image channels as follows:
        # self.DicoMSChanMappingDegridding: a dict, indexed by MS number
        #       [iMS] = int array mapping MS channel numbers into model channel numbers (0...M-1)
        # self.FreqBandChannelsDegrid: a dict, indexed by MS number
        #       [iMS] = float32 array of M frequencies corresponding to M model channels for this MS
        # self.FreqBandChannels: a list, indexed by freq band number (N=NFreqBands items)
        #       [iband] = list of frequency channels that fall within that band
        # self.FreqBandCenters: a list of centre frequencies per each band (N=NFreqBands items)
        #       [iband] = centre frequency of that output band
        # self.DicoMSChanMapping: a dict, indexed by MS number
        #       [iMS] = int array mapping MS channel numbers to output band numbers
        # self.DicoMSChanMappingChan: a dict, indexed by MS number
        #       [iMS] = int array mapping MS channel numbers to channel number within the corresponding output band

        for iMS, MS in enumerate(self.ListMS):
            min_freq = (MS.ChanFreq - MS.ChanWidth/2).min()
            max_freq = (MS.ChanFreq + MS.ChanWidth/2).max()
            bw = max_freq - min_freq
            # print>>log,bw,min_freq,max_freq
            # map each channel to a gridding band
            bands = [freq_to_grid_band[freq] for freq in MS.ChanFreq]
            self.DicoMSChanMapping[iMS] = np.array(bands)
            self.DicoMSChanMappingChan[iMS] = np.array(
                [freq_to_grid_band_chan[freq] for freq in MS.ChanFreq])

            # OMS: new option, DegridBandMHz specifies degridding band step. If
            # 0, fall back to NChanDegridPerMS
            degrid_bw = self.GD["Freq"]["DegridBandMHz"]*1e+6
            if degrid_bw:
                degrid_bw = min(degrid_bw, bw)
                degrid_bw = max(degrid_bw, MS.ChanWidth[0])
                NChanDegrid = min(
                    int(math.ceil(bw / degrid_bw)),
                    MS.ChanFreq.size)
            else:
                NChanDegrid = min(
                    self.GD["Freq"]["NDegridBand"]
                    or MS.ChanFreq.size, MS.ChanFreq.size)
                degrid_bw = bw/NChanDegrid

            # now map each channel to a degridding band
            self.DicoMSChanMappingDegridding[iMS] = np.floor(
                (MS.ChanFreq - min_freq)/degrid_bw).astype(int)

            # calculate center frequency of each degridding band
            edges = np.arange(min_freq, max_freq+degrid_bw, degrid_bw)
            self.FreqBandChannelsDegrid[iMS] = (edges[:-1] + edges[1:])/2

            print>>log, "%s   Bandwidth is %g MHz (%g to %g MHz), gridding bands are %s" % (
                MS, bw*1e-6, min_freq*1e-6, max_freq*1e-6, ", ".join(map(str, set(bands))))
            print>>log, "Grid band mapping: %s" % (" ".join(map(str, bands)))
            print >>log, "Grid chan mapping: %s" % (
                " ".join(map(str, self.DicoMSChanMappingChan[iMS])))
            print >>log, "Degrid chan mapping: %s" % (
                " ".join(map(str, self.DicoMSChanMappingDegridding[iMS])))
            print >>log, "Degrid frequencies: %s" % (" ".join(
                                                         ["%.2f" %
                                                          (x * 1e-6)
                                                          for x in self.FreqBandChannelsDegrid
                                                          [iMS]]))

#            print>>log,MS

            # print>>log,"FreqBandChannelsDegrid %s"%repr(self.FreqBandChannelsDegrid[iMS])
            # print>>log,"self.DicoMSChanMappingDegriding %s"%repr(self.DicoMSChanMappingDegridding[iMS])
            # print>>log,"self.DicoMSChanMapping %s"%repr(self.DicoMSChanMapping[iMS])

        # print>>log,"FreqBandChannels %s"%repr(self.FreqBandChannels)

#        self.RefFreq=np.mean(self.ListFreqs)
        self.RefFreq = np.mean(self.GlobalFreqs)

        self.ReInitChunkCount()

        # TimesVisMin=np.arange(0,MS.DTh*60.,self.TVisSizeMin).tolist()
        #if not(MS.DTh*60. in TimesVisMin): TimesVisMin.append(MS.DTh*60.)
        # self.TimesVisMin=np.array(TimesVisMin)

    def SetImagingPars(self, OutImShape, CellSizeRad):
        self.OutImShape = OutImShape
        self.CellSizeRad = CellSizeRad

    def CalcMeanBeam(self):
        AverageBeamMachine = ClassBeamMean.ClassBeamMean(self)
        AverageBeamMachine.LoadData()
        AverageBeamMachine.CalcMeanBeam()

    # def VisChunkToShared(self):
    #
    #     D = self.ThisDataChunk
    #     DATA = {}
    #     for key,entry in D.iteritems():
    #         # data and flags is not stored in shared memory
    #         if not isinstance(D[key], np.ndarray) or key == "data" or key == "flags":
    #             continue
    #         # if not(
    #         #    key in [
    #         #        'times',
    #         #        'A1',
    #         #        'A0',
    #         #        'flagpath',
    #         #        'uvw',
    #         #        'datapath',
    #         #        "uvw_dt",
    #         #        "MSInfos",
    #         #        "ChanMapping",
    #         #        "ChanMappingDegrid"]):
    #         DATA[key] = entry
    #
    #
    #     if "DicoBeam" in D.keys():
    #         DATA["DicoBeam"] = D["DicoBeam"]
    #
    #     #print>>log, "!!!!!!!!!"
    #     # DATA["flags"].fill(0)
    #
    #     print>>log, "Putting data in shared memory"
    #     DATA = NpShared.DicoToShared("%sDicoData" % self.IdSharedMem, DATA)
    #
    #     return DATA

    def ReInitChunkCount(self):
        self.iCurrentMS = 0
        self.iCurrentChunk = 0
        self.CurrentFreqBand = 0
        for MS in self.ListMS:
            MS.ReinitChunkIter()
        self.CurrentMS = self.ListMS[0]
        self.CurrentChanMapping = self.DicoMSChanMapping[0]
        self.CurrentChanMappingDegrid = self.FreqBandChannelsDegrid[0]
        #print>>log, (ModColor.Str("NextMS %s"%(self.CurrentMS.MSName),col="green") + (" --> freq. band %i"%self.CurrentFreqBand))

    def setNextMS(self):
        if (self.iCurrentMS+1) == self.nMS:
            print>>log, ModColor.Str("Reached end of MSList")
            return "EndListMS"
        else:
            self.iCurrentMS += 1
            self.CurrentMS = self.ListMS[self.iCurrentMS]
            self.CurrentChanMapping = self.DicoMSChanMapping[self.iCurrentMS]
            self.CurrentChanMappingDegrid = self.FreqBandChannelsDegrid[
                self.iCurrentMS]
            return "OK"

    def getVisibilityData (self):
        """Returns array of visibility data for current chunk. Note that this can only be called if
        LoadNextVisChunk() was called with keep_data=True."""
        if "orig_data" not in self.DATA:
            raise RuntimeError("original data requested but keep_data was not specified. This is a bug.")
        return self.DATA["orig_data"]

    def getVisibilityResiduals (self):
        """Returns array of visibility residuals for current chunk."""
        return self.DATA["data"]

    def LoadNextVisChunk(self, keep_data=False, null_data=False):
        """
        Loads next visibility chunk (from current MS or next MS). Populates self.DATA with a dict
        of the visibilities and associated metadata.

        Args:
            keep_data: if True, then we want to keep a separate copy of the visibilities (retrieved
                by getOriginalData()) above. Normally the visibility buffer is modified during degridding
                (overwritten by residuals). If we want to retain the original data (e.g. for computing the
                predict), we set keep_data=True.

            null_data: if True, then we don't want to read the visibility data at all, but rather just want to make
                a null buffer of the same shape as the visibility data.

        Returns:
            DATA object (dict) the next chunk is loaded. Otherwise, a string indicating the end-of-data condition.
            ("EndOfObservaton", etc.)

        """
        self.residual_data = self.orig_data = self.orig_datapath = None
        self.datapath = Multiprocessing.getShmURL("Data")
        if self._databuf is None:
            self._databuf = NpShared.CreateShared(self.datapath, self._chunk_shape, np.complex64)
        if self._flagbuf is None:
            self._flagbuf = np.empty(self._chunk_shape, np.bool)

        while True:
            MS = self.CurrentMS
            repLoadChunk = MS.GiveNextChunk(
                databuf=self._databuf, 
                flagbuf=self._flagbuf,
                use_cache=self._use_data_cache,
                read_data=not null_data,
                sort_by_baseline=self.GD["Data"]["Sort"])
            self.cache = MS.cache
            if repLoadChunk == "EndMS":
                repNextMS = self.setNextMS()
                if repNextMS == "EndListMS":
                    print>>log, ModColor.Str("Reached end of Observation")
                    self.ReInitChunkCount()
                    return "EndOfObservation"
                elif repNextMS == "OK":
                    continue
            DATA = repLoadChunk
            ## now load weights. Note that an all-flagged chunk of data is markjed by a null weights file.
            ## so we check it here to go on to the next chunk as needed
            # weightspath = self.GetVisWeightsPath(self.iCurrentMS, self.CurrentMS.current_chunk)
            # if not os.path.getsize(weightspath):
            #     print>> log, ModColor.Str("This chunk is all flagged or has zero weight, skipping it")
            #     continue
            # # mmap() arrays caused mysterious performance hits, so load and copy
            # DATA["Weights"] = NpShared.GiveArray("file://" + weightspath).copy()
            weights = self.GetVisWeights(self.iCurrentMS, self.CurrentMS.current_chunk)
            if weights is None:
                print>> log, ModColor.Str("This chunk is all flagged or has zero weight, skipping it")
                continue
            # mmap() arrays caused mysterious performance hits, so load and copy
            DATA["Weights"] = weights
            if DATA["sort_index"] is not None:
                DATA["Weights"] = DATA["Weights"][DATA["sort_index"]]
            break
        print>> log, ModColor.Str("processing ms %d of %d, chunk %d of %d" % (
            self.iCurrentMS + 1, self.nMS, self.CurrentMS.current_chunk+1, self.CurrentMS.Nchunk), col="green")

        times = DATA["times"]
        data = DATA["data"]
        A0 = DATA["A0"]
        A1 = DATA["A1"]

        freqs = MS.ChanFreq.flatten()
        nbl = MS.nbl
        self.datashape = data.shape

        # if requested to keep a copy of original data, make one now
        if keep_data:
            DATA["orig_data"] = data.copy()

        # ## debug
        # ind=np.where((A0==14)&(A1==31))[0]
        # flags=flags[ind]
        # data=data[ind]
        # A0=A0[ind]
        # A1=A1[ind]
        # uvw=uvw[ind]
        # times=times[ind]
        # ##

        DecorrMode = self.GD["DDESolutions"]["DecorrMode"]

        if 'F' in DecorrMode or "T" in DecorrMode:
            DATA["uvw_dt"]  = np.float64(self.CurrentMS.Give_dUVW_dt(times,A0,A1))
            DATA["MSInfos"] = np.array([repLoadChunk["dt"],repLoadChunk["dnu"].ravel()[0]],np.float32)
            #DATA["MSInfos"][1]=20000.*30
            #DATA["MSInfos"][0]=500.

        # # flagging cache depends on DicoSelectOptions
        # flagpath, valid = self.cache.checkCache(
        #     "Flagging.npy", self.DicoSelectOptions)
        # if valid:
        #     print>> log, "  using cached flags from %s" % flagpath
        #     DATA["flags"] = np.load(flagpath)
        # else:
        #     self.UpdateFlag(DATA)
        #     np.save(flagpath, DATA["flags"])
        #     self.cache.saveCache("Flagging.npy")

        DATA["ChanMapping"] = self.CurrentChanMapping
        DATA["ChanMappingDegrid"] = self.DicoMSChanMappingDegridding[self.iCurrentMS]

        print>>log, "  channel Mapping Gridding  : %s" % str(self.CurrentChanMapping)
        print>>log, "  channel Mapping DeGridding: %s" % str(DATA["ChanMappingDegrid"])

        self.UpdateCompression(DATA, ChanMappingGridding=DATA["ChanMapping"],
            ChanMappingDeGridding=self.DicoMSChanMappingDegridding[self.iCurrentMS])

        JonesMachine = ClassJones.ClassJones(self.GD, self.CurrentMS, self.FacetMachine)
        JonesMachine.InitDDESols(DATA)

        if self.AddNoiseJy is not None:
            data += (self.AddNoiseJy/np.sqrt(2.)
                     )*(np.random.randn(*data.shape)+1j*np.random.randn(*data.shape))

        if freqs.size > 1:
            DATA["freqs"] = np.float64(freqs)
        else:
            DATA["freqs"] = np.array([freqs[0]], dtype=np.float64)

        DATA["nbl"]   = nbl
        DATA["na"]    = MS.na
        DATA["ROW0"]  = MS.ROW0
        DATA["ROW1"]  = MS.ROW1

        self.DATA = DATA

        return DATA

    def setFacetMachine(self, FacetMachine):
        self.FacetMachine = FacetMachine
        self.FullImShape = self.FacetMachine.OutImShape
        self.PaddedFacetShape = self.FacetMachine.PaddedGridShape
        self.FacetShape = self.FacetMachine.FacetShape
        self.CellSizeRad = self.FacetMachine.CellSizeRad

    def setFOV(self, sh0, sh1, sh2, cell):
        self.FullImShape = sh0
        self.PaddedFacetShape = sh1
        self.FacetShape = sh2
        self.CellSizeRad = cell

    def UpdateCompression(self, DATA, ChanMappingGridding=None, ChanMappingDeGridding=None):
        if True: # always True for now, non-BDA gridder is not maintained # if self.GD["Comp"]["CompGridMode"]:
            mapname, valid = self.cache.checkCache("BDA.Grid",
                                                   dict(Compression=self.GD["Comp"],
                                                        DataSelection=self.GD["Selection"],
                                                        Sorting=self.GD["Data"]["Sort"]))
            if valid:
                print>> log, "  using cached BDA mapping %s" % mapname
                DATA["BDAGrid"] = np.load(mapname)
            else:
                if self.GD["Comp"]["GridFoV"] == "Facet":
                    _, _, nx, ny = self.FacetShape
                elif self.GD["Comp"]["GridFoV"] == "Full":
                    _, _, nx, ny = self.FullImShape
                FOV = self.CellSizeRad * nx * (np.sqrt(2.) / 2.) * 180. / np.pi
                SmearMapMachine = ClassSmearMapping.ClassSmearMapping(
                    self.CurrentMS, radiusDeg=FOV,
                    Decorr=(1. - self.GD["Comp"]["GridDecorr"]))
                FinalMapping, fact = SmearMapMachine.BuildSmearMappingParallel(DATA, ChanMappingGridding)

                print>> log, ModColor.Str("  Effective compression [grid]  :   %.2f%%" % fact, col="green")

                DATA["BDAGrid"] = FinalMapping
                np.save(file(mapname, 'w'), FinalMapping)
                self.cache.saveCache("BDA.Grid")

        if True: # always True for now, non-BDA gridder is not maintained # if self.GD["Comp"]["CompDeGridMode"]:
            mapname, valid = self.cache.checkCache("BDA.DeGrid",
                                                   dict(Compression=self.GD["Comp"],
                                                        DataSelection=self.GD["Selection"],
                                                        Sorting=self.GD["Data"]["Sort"]))
            if valid:
                print>> log, "  using cached BDA mapping %s" % mapname
                DATA["BDADegrid"] = np.load(mapname)
            else:
                if self.GD["Comp"]["DegridFoV"] == "Facet":
                    _, _, nx, ny = self.FacetShape
                elif self.GD["Comp"]["DegridFoV"] == "Full":
                    _, _, nx, ny = self.FullImShape
                FOV = self.CellSizeRad * nx * (np.sqrt(2.) / 2.) * 180. / np.pi
                SmearMapMachine = ClassSmearMapping.ClassSmearMapping(
                    self.CurrentMS, radiusDeg=FOV,
                    Decorr=(1. - self.GD["Comp"]["DegridDecorr"]))
                FinalMapping, fact = SmearMapMachine.BuildSmearMappingParallel(DATA, ChanMappingDeGridding)
                print>> log, ModColor.Str("  Effective compression [degrid]:   %.2f%%" %fact, col="green")
                DATA["BDADegrid"] = FinalMapping
                np.save(file(mapname, 'w'), FinalMapping)
                self.cache.saveCache("BDA.DeGrid")

    def GetVisWeights(self, iMS, iChunk):
        """
        Returns path to weights array for the given MS and chunk number.

        Waits for CalcWeights to complete (if running in background).
        """
        if self.VisWeights is None:
            # ensure the background calculation is complete
            self.APP.awaitEvents("VisWeights")
            # load shared dict prepared in background thread
            self.VisWeights = SharedDict("VisWeights",  reset=False)
        path = self.VisWeights[iMS][iChunk]
        if not os.path.getsize(path):
            return None
        return np.load(file(path))

    def CalcWeightsBackground (self):
        self.APP.runJob("VisWeights", "VS.CalcWeights", io=0, event="VisWeights")

    def CalcWeights(self):
        """
        Calculates visibility weights. This can be run in a main or background process.
        """
        if self.VisWeights is not None:
            return

        # in RAM-greedy mode, we keep all weight arrays around in RAM while computing weights
        # Otherwise we leave them in mmap()ed files and etach, and let the
        # kernel take care of caching etc.
        greedy = self.GD["Debug"]["MemoryGreedy"]

        # check if every MS+chunk weight is available in cache
        self.VisWeights = SharedDict("VisWeights", reset=True)
        have_all_weights = True
        for iMS,MS in enumerate(self.ListMS):
            msweights = []
            for row0, row1 in MS.getChunkRow0Row1():
                cachepath, valid = MS.getChunkCache(row0, row1).checkCache("ImagingWeights.npy",
                    dict([(section, self.GD[section]) for section in ("Data", "Selection", "Freq", "Image")]))
                have_all_weights = have_all_weights and valid
                msweights.append(cachepath)
            self.VisWeights[iMS] = msweights
        # if every weight is in cache, then VisWeights has been constructed properly -- return, else
        # carry on to compute it
        if have_all_weights:
            print>> log, "all imaging weights are available in cache"
            return

        weight_arrays = {}

        # VisWeights is a list of per-MS lists, each list containing a per-chunk
        # cache filename

        # Read UVs, weights, flags, freqs from all MSs in the list.
        # Form up output_list of (uv,weights,flags,freqs) tuples, one per each MS in self.ListMS, where shapes are
        # (nrow,2), (nrow,nchan), (nrow) and (nchan) respectively.
        # Note that flags are "row flags" i.e. only True if all channels are flagged.
        # Per-channel flagging is taken care of in here, by setting that
        # channel's weight to 0.

        WeightCol = self.GD["Data"]["WeightCol"]
        # now loop over MSs and read data
        weightsum = nweights = 0
        weights_are_null = True
        output_list = []
        for ims, ms in enumerate(self.ListMS):
            ms_weight_list = self.VisWeights[iMS]
            tab = ms.GiveMainTable()
            for (row0, row1), cachepath in zip(ms.getChunkRow0Row1(), ms_weight_list):
                nrows = row1 - row0
                chanslice = ms.ChanSlice
                if not nrows:
                    # if no data in this chunk, make single, flagged entry
                    output_list.append( (np.zeros((1, 2)),
						 np.zeros((1, len(ms.ChanFreq))),
                         np.array([True]), 
                         ms.ChanFreq))
                    continue
                print>>log,"  reading %s UVW" % ms.MSName
                uvs = tab.getcol("UVW", row0, nrows)[:, :2]
                flags = np.empty((nrows, len(ms.ChanFreq), len(ms.CorrelationIds)), np.bool)
                # print>>log,(ms.cs_tlc,ms.cs_brc,ms.cs_inc,flags.shape)
                print>>log,"  reading %s FLAG" % ms.MSName
                tab.getcolslicenp("FLAG", flags, ms.cs_tlc, ms.cs_brc, ms.cs_inc, row0, nrows)
                print>>log,"  adjusting flags"
                # if any polarization is flagged, flag all 4 correlations. Shape
                # of flags becomes nrow,nchan
                flags = flags.max(axis=2)
                # valid: array of Nrow,Nchan, with meaning inverse to flags
                valid = ~flags
                # if all channels are flagged, flag whole row. Shape of flags
                # becomes nrow
                flags = flags.min(axis=1)

                # # each weight is kept in an mmap()ed file in the cache, shape
                # # (nrows,nchan)
                # weightpath = "file://"+cachepath

                # if everything is flagged, skip this entry, and mark it with a zero-length weights file
                if flags.all() or not nrows:
                    # Nones tell CalcWeights to skip this chunk entirely
                    output_list.append((uvs, None, None, ms.ChanFreq))
                    # make an empty weights file in the cache
                    file(cachepath,'w').truncate(0)
                    continue

                # WEIGHT = NpShared.CreateShared(weightpath, (nrows, ms.Nchan), np.float64)
                weight_arrays[cachepath] = WEIGHT = np.zeros((nrows, ms.Nchan), np.float64)

                if WeightCol == "WEIGHT_SPECTRUM":
                    w = tab.getcol(WeightCol, row0, nrows)[:, chanslice]
                    print>> log, "  reading column %s for the weights, shape is %s" % (
                        WeightCol, w.shape)
                    # take mean weight across correlations and apply this to all
                    WEIGHT[...] = w.mean(axis=2) * valid
                elif WeightCol == "WEIGHT":
                    w = tab.getcol(WeightCol, row0, nrows)
                    print>> log, "  reading column %s for the weights, shape is %s, will expand frequency axis" % (
                        WeightCol, w.shape)
                    # take mean weight and apply this to all correlations, and
                    # expand to have frequency axis
                    WEIGHT[...] = w.mean(axis=1)[:, np.newaxis] * valid
                else:
                    # in all other cases (i.e. IMAGING_WEIGHT) assume a column
                    # of shape NRow,NFreq to begin with, check for this:
                    w = tab.getcol(WeightCol, row0, nrows)[:, chanslice]
                    print>> log, "  reading column %s for the weights, shape is %s" % (
                        WeightCol, w.shape)
                    if w.shape != valid.shape:
                        raise TypeError(
                            "weights column expected to have shape of %s" %
                            (valid.shape,))
                    WEIGHT[...] = w*valid

                weightsum = weightsum + WEIGHT.sum(dtype=np.float64)
                nweights += valid.sum()
                weights_are_null = weights_are_null and (WEIGHT == 0).all()

                output_list.append((uvs, WEIGHT if greedy else cachepath, flags, ms.ChanFreq))
                if greedy:
                    del WEIGHT
            tab.close()

        # compute normalization factor
        weightnorm = nweights / weightsum if weightsum else 1
        print>> log, "weight norm is %g (sum %g from %d valid visibility points)" % (
            weightnorm, weightsum, nweights)

        # now compute actual imaging weights
        ImShape = self.FullImShape  # self.FacetShape
        CellSizeRad = self.CellSizeRad
        WeightMachine = ClassWeighting.ClassWeighting(ImShape, CellSizeRad)
        Robust = self.Robust

        if self.MFSWeighting or self.NFreqBands < 2:
            band_mapping = None
        else:
            # we need provide a band mapping for every chunk of weights, so construct a list
            # where each MS's mapping is repeated Nchunk times
            band_mapping = []
            for i, ms in enumerate(self.ListMS):
                band_mapping += [self.DicoMSChanMapping[i]] * ms.Nchunk

        WeightMachine.CalcWeights(
            output_list, 
            Robust=Robust, 
            Weighting=self.Weighting,
            Super=self.Super, 
            nbands=self.NFreqBands if band_mapping is not None else 1, 
            band_mapping=band_mapping,
            weightnorm=weightnorm, 
            force_unity_weight=weights_are_null)

        # # done, every weight array in output_list has been normalized to proper imaging weights
        # # we now release the arrays, which will flush the buffers to disk
        # # (eventually)
        # del output_list
        for path, array in weight_arrays.iteritems():
            print>>log,"saving %s"%path
            np.save(path, array)
        # so now we can mark the cache as safe
        for MS in self.ListMS:
            for row0, row1 in MS.getChunkRow0Row1():
                MS.getChunkCache(row0, row1).saveCache("ImagingWeights.npy")