from nose.tools import *
from DDFacet.Data.ClassStokes import *

def testSetupWithIQUVString():
    conv = ClassStokes([StokesTypes["XX"], StokesTypes["XY"], StokesTypes["YX"], StokesTypes["YY"]],
                       "IQUV")
    assert conv._MSDataDescriptor == [StokesTypes["XX"], StokesTypes["XY"], StokesTypes["YX"], StokesTypes["YY"]]
    assert conv._MScorrLabels == ["XX","XY","YX","YY"]
    assert conv._gridMSCorrMapping == {StokesTypes["XX"]:0, StokesTypes["XY"]:1,
                                       StokesTypes["YX"]:2, StokesTypes["YY"]:3}
    assert conv._FITSstokesList == ["I","Q","U","V"]
    assert conv._stokesExpr == [2,2,2,2]
    assert [StokesDependencies["I"][conv._stokesExpr[0]][0],
            StokesDependencies["I"][conv._stokesExpr[0]][1]] == [StokesTypes["XX"],StokesTypes["YY"]]
    assert [StokesDependencies["Q"][conv._stokesExpr[1]][0],
            StokesDependencies["Q"][conv._stokesExpr[1]][1]] == [StokesTypes["XX"], StokesTypes["YY"]]
    assert [StokesDependencies["U"][conv._stokesExpr[2]][0],
            StokesDependencies["U"][conv._stokesExpr[2]][1]] == [StokesTypes["XY"], StokesTypes["YX"]]
    assert [StokesDependencies["V"][conv._stokesExpr[3]][0],
            StokesDependencies["V"][conv._stokesExpr[3]][1]] == [StokesTypes["XY"], StokesTypes["YX"]]
    assert conv._FITSstokesSliceLookup[StokesTypes["V"]] == 3
    assert conv._FITSstokesSliceLookup[StokesTypes["I"]] == 0
    assert conv._FITSstokesSliceLookup[StokesTypes["Q"]] == 1
    assert conv._FITSstokesSliceLookup[StokesTypes["U"]] == 2

def testSetupWithIQUVString2():
    conv = ClassStokes([StokesTypes["XX"], StokesTypes["XY"], StokesTypes["YX"], StokesTypes["YY"]],
                       "IVUQ")
    assert conv._MSDataDescriptor == [StokesTypes["XX"], StokesTypes["XY"], StokesTypes["YX"], StokesTypes["YY"]]
    assert conv._MScorrLabels == ["XX","XY","YX","YY"]
    assert conv._FITSstokesList == ["I","V","U","Q"]
    assert conv._gridMSCorrMapping == {StokesTypes["XX"]: 0, StokesTypes["XY"]: 1,
                                       StokesTypes["YX"]: 2, StokesTypes["YY"]: 3}
    assert conv._stokesExpr == [2, 2, 2, 2]
    assert [StokesDependencies["I"][conv._stokesExpr[0]][0],
            StokesDependencies["I"][conv._stokesExpr[0]][1]] == [StokesTypes["XX"], StokesTypes["YY"]]
    assert [StokesDependencies["V"][conv._stokesExpr[1]][0],
            StokesDependencies["V"][conv._stokesExpr[1]][1]] == [StokesTypes["XY"], StokesTypes["YX"]]
    assert [StokesDependencies["Q"][conv._stokesExpr[2]][0],
            StokesDependencies["Q"][conv._stokesExpr[2]][1]] == [StokesTypes["XX"], StokesTypes["YY"]]
    assert [StokesDependencies["U"][conv._stokesExpr[3]][0],
            StokesDependencies["U"][conv._stokesExpr[3]][1]] == [StokesTypes["XY"], StokesTypes["YX"]]
    assert conv._FITSstokesSliceLookup[StokesTypes["V"]] == 1
    assert conv._FITSstokesSliceLookup[StokesTypes["I"]] == 0
    assert conv._FITSstokesSliceLookup[StokesTypes["Q"]] == 3
    assert conv._FITSstokesSliceLookup[StokesTypes["U"]] == 2

def testSetupWithIQUVString3():
    conv = ClassStokes([StokesTypes["RL"], StokesTypes["LR"]],
                       "QU")
    assert conv._MSDataDescriptor == [StokesTypes["RL"], StokesTypes["LR"]]
    assert conv._MScorrLabels == ["RL","LR"]
    assert conv._gridMSCorrMapping == {StokesTypes["RL"]: 0, StokesTypes["LR"]: 1}
    assert conv._FITSstokesList == ["Q","U"]
    assert conv._stokesExpr == [1, 1]
    assert [StokesDependencies["Q"][conv._stokesExpr[0]][0],
            StokesDependencies["Q"][conv._stokesExpr[0]][1]] == [StokesTypes["RL"], StokesTypes["LR"]]
    assert [StokesDependencies["U"][conv._stokesExpr[1]][0],
            StokesDependencies["U"][conv._stokesExpr[1]][1]] == [StokesTypes["RL"], StokesTypes["LR"]]
    assert conv._FITSstokesSliceLookup[StokesTypes["U"]] == 1
    assert conv._FITSstokesSliceLookup[StokesTypes["Q"]] == 0

def testSetupWithIQUVString4():
    conv = ClassStokes([StokesTypes["I"], StokesTypes["U"]],
                       "UI")
    assert conv._MSDataDescriptor == [StokesTypes["I"], StokesTypes["U"]]
    assert conv._MScorrLabels == ["I","U"]
    assert conv._gridMSCorrMapping == {StokesTypes["I"]: 0, StokesTypes["U"]: 1}
    assert conv._FITSstokesList == ["U","I"]
    assert conv._stokesExpr == [0, 0]
    assert [StokesDependencies["U"][conv._stokesExpr[0]][0]] == [StokesTypes["U"]]
    assert [StokesDependencies["I"][conv._stokesExpr[1]][0]] == [StokesTypes["I"]]
    assert conv._FITSstokesSliceLookup[StokesTypes["U"]] == 0
    assert conv._FITSstokesSliceLookup[StokesTypes["I"]] == 1

def testSetupWithList():
    conv = ClassStokes([StokesTypes["XX"], StokesTypes["XY"], StokesTypes["YX"], StokesTypes["YY"]],
                       ["XX","YY","XY","YX"])
    assert conv._MSDataDescriptor == [StokesTypes["XX"], StokesTypes["XY"], StokesTypes["YX"], StokesTypes["YY"]]
    assert conv._MScorrLabels == ["XX","XY","YX","YY"]
    assert conv._gridMSCorrMapping == {StokesTypes["XX"]: 0, StokesTypes["XY"]: 1,
                                       StokesTypes["YX"]: 2, StokesTypes["YY"]: 3}
    assert conv._FITSstokesList == ["XX","YY","XY","YX"]
    assert conv._stokesExpr == [0, 0, 0, 0]
    assert [StokesDependencies["XX"][conv._stokesExpr[0]][0]] == [StokesTypes["XX"]]
    assert [StokesDependencies["YY"][conv._stokesExpr[1]][0]] == [StokesTypes["YY"]]
    assert [StokesDependencies["XY"][conv._stokesExpr[2]][0]] == [StokesTypes["XY"]]
    assert [StokesDependencies["YX"][conv._stokesExpr[3]][0]] == [StokesTypes["YX"]]
    assert conv._FITSstokesSliceLookup[StokesTypes["XX"]] == 0
    assert conv._FITSstokesSliceLookup[StokesTypes["YY"]] == 1
    assert conv._FITSstokesSliceLookup[StokesTypes["XY"]] == 2
    assert conv._FITSstokesSliceLookup[StokesTypes["YX"]] == 3

def testGridMapping():
    conv = ClassStokes([StokesTypes["XY"], StokesTypes["XX"], StokesTypes["YY"], StokesTypes["YX"]], #non-standard enumeration
                       ["I", "U", "Q", "V"])
    assert conv._gridMSCorrMapping == {StokesTypes["XX"]: 1, StokesTypes["XY"]: 0,
                                       StokesTypes["YX"]: 3, StokesTypes["YY"]: 2}
    assert conv._stokesExpr == [2, 2, 2, 2]
    assert [StokesDependencies["I"][conv._stokesExpr[0]][0],
            StokesDependencies["I"][conv._stokesExpr[0]][1]] == [StokesTypes["XX"], StokesTypes["YY"]]
    assert [StokesDependencies["U"][conv._stokesExpr[1]][0],
            StokesDependencies["U"][conv._stokesExpr[1]][1]] == [StokesTypes["XY"], StokesTypes["YX"]]
    assert [StokesDependencies["Q"][conv._stokesExpr[2]][0],
            StokesDependencies["Q"][conv._stokesExpr[2]][1]] == [StokesTypes["XX"], StokesTypes["YY"]]
    assert [StokesDependencies["V"][conv._stokesExpr[3]][0],
            StokesDependencies["V"][conv._stokesExpr[3]][1]] == [StokesTypes["XY"], StokesTypes["YX"]]
    assert conv._FITSstokesSliceLookup[StokesTypes["I"]] == 0
    assert conv._FITSstokesSliceLookup[StokesTypes["U"]] == 1
    assert conv._FITSstokesSliceLookup[StokesTypes["Q"]] == 2
    assert conv._FITSstokesSliceLookup[StokesTypes["V"]] == 3

@raises(ValueError)
def testDependenciesNotSatisfied():
    conv = ClassStokes([StokesTypes["XX"], StokesTypes["YY"]],
                       "IU")
@raises(ValueError)
def testDependenciesNotSatisfiedRRwithLinear():
    conv = ClassStokes([StokesTypes["XX"], StokesTypes["YY"]],
                       ["XX","RR"])
@raises(ValueError)
def testInvalidImageStokes():
    conv = ClassStokes([StokesTypes["XX"], StokesTypes["XY"], StokesTypes["YX"], StokesTypes["YY"]],
                       "IQUVW")
@raises(ValueError)
def testInvalidImageStokesList():
    conv = ClassStokes([StokesTypes["XX"], StokesTypes["XY"], StokesTypes["YX"], StokesTypes["YY"]],
                       ["I","V","YL"])
@raises(ValueError)
def testUnsupportedMeasurementSetCorrelation():
    conv = ClassStokes([StokesTypes["XX"], StokesTypes["XY"], StokesTypes["YX"], 0],
                       "IQUV")
@raises(ValueError)
def testCannotReconstructCorrelationXYYX():
    conv = ClassStokes([StokesTypes["XY"], StokesTypes["XX"], StokesTypes["YY"], StokesTypes["YX"]], #non-standard enumeration
                       ["I", "Q"])
@raises(ValueError)
def testCannotReconstructCorrelationXXYY():
    conv = ClassStokes([StokesTypes["XY"], StokesTypes["XX"], StokesTypes["YY"], StokesTypes["YX"]], #non-standard enumeration
                       ["V", "U"])
@raises(ValueError)
def testCannotReconstructCorrelationRRLL():
    conv = ClassStokes([StokesTypes["RR"], StokesTypes["RL"], StokesTypes["LR"], StokesTypes["LL"]], #non-standard enumeration
                       ["U", "V"])
@raises(ValueError)
def testCannotReconstructCorrelationRLLR():
    conv = ClassStokes([StokesTypes["RR"], StokesTypes["RL"], StokesTypes["LR"], StokesTypes["LL"]], #non-standard enumeration
                       ["I", "Q"])

def testExpExtraction():
    g = ClassStokes._extractStokesCombinationExpression([5, 6,"0.5i(0+1)"])
    assert g == (0.5, 0+1j, 5, np.add, 6, 1, 1)
    g = ClassStokes._extractStokesCombinationExpression([5, 6, "0.5i(0-1)"])
    assert g == (0.5, 0 + 1j, 5, np.subtract, 6, 1, 1)
    g = ClassStokes._extractStokesCombinationExpression([5, 6, "i(0+1)"])
    assert g == (1, 0 + 1j, 5, np.add, 6, 1, 1)
    g = ClassStokes._extractStokesCombinationExpression([5, 6, "3(0+1)"])
    assert g == (3, 1, 5, np.add, 6, 1, 1)
    g = ClassStokes._extractStokesCombinationExpression([5, "3(0)"])
    assert (g[0], g[1], g[2], g[5], g[6]) == (3, 1, 5, 1, 1) and g[3](g[2],g[4]) == 5
    g = ClassStokes._extractStokesCombinationExpression([5, "(0)"])
    assert (g[0], g[1], g[2], g[5], g[6]) == (1, 1, 5, 1, 1) and g[3](g[2], g[4]) == 5
    g = ClassStokes._extractStokesCombinationExpression([5, "(i0)"])
    assert (g[0], g[1], g[2], g[5], g[6]) == (1, 1, 5, 1j, 1) and g[3](g[2], g[4]) == 5
    g = ClassStokes._extractStokesCombinationExpression([5, 6, "0.5i(i0+1)"])
    assert g == (0.5, 0 + 1j, 5, np.add, 6, 1j, 1)
    g = ClassStokes._extractStokesCombinationExpression([5, 6, "0.5i(0+i1)"])
    assert g == (0.5, 0 + 1j, 5, np.add, 6, 1, 1j)
    g = ClassStokes._extractStokesCombinationExpression([5, 6, "0.5i(i0+i1)"])
    assert g == (0.5, 0 + 1j, 5, np.add, 6, 1j, 1j)

@raises(ValueError)
def testExpExtractTooFewArgs():
    g = ClassStokes._extractStokesCombinationExpression(["0.5i(0+1)"])

@raises(ValueError)
def testExpExtractMalformedExp():
    g = ClassStokes._extractStokesCombinationExpression([5, "ai(0+1)"])

@raises(ValueError)
def testExpExtractMalformedExp2():
    g = ClassStokes._extractStokesCombinationExpression([5, "3i(0 1)"])

@raises(ValueError)
def testExpExtractMalformedExp3():
    g = ClassStokes._extractStokesCombinationExpression([5, "3i(a+b)"])

def testCubeTransformCorrs2StokesLinear():
    conv = ClassStokes([StokesTypes["XX"], StokesTypes["XY"], StokesTypes["YX"], StokesTypes["YY"]],
                       "IQUV")
    corrCube = np.zeros([1,4,1,3],dtype=np.complex64)
    corrCube[:, 0, :, 0] = 2; corrCube[:, 3, :, 0] = 0 #full horizontal (Q = 1)
    corrCube[:, 0, :, 1] = 1; corrCube[:, 1, :, 1] = 1; corrCube[:, 2, :, 1] = 1; corrCube[:, 3, :, 1] = 1 # full 45 linear (U = 1)
    corrCube[:, 0, :, 2] = 1; corrCube[:, 1, :, 2] = 1j*1; corrCube[:, 2, :, 2] = -1j*1; corrCube[:, 3, :, 2] = 1 #full right circular (V = 1)
    stokesCube = conv.corrs2stokes(corrCube)
    assert np.allclose(stokesCube[0, :, 0, 0], np.array([1+0j, 1+0j, 0, 0]))
    assert np.allclose(stokesCube[0, :, 0, 1], np.array([1+0j, 0, 1+0j, 0]))
    assert np.allclose(stokesCube[0, :, 0, 2], np.array([1+0j, 0, 0, 1+0j]))

def testCubeTransformCorrs2StokesCircular():
    conv = ClassStokes([StokesTypes["RR"], StokesTypes["RL"], StokesTypes["LR"], StokesTypes["LL"]],
                       "IQUV")
    corrCube = np.zeros([1, 4, 1, 3], dtype=np.complex64)
    corrCube[:, 0, :, 0] = 2; corrCube[:, 3, :, 0] = 0  # full right circular (V = 1)
    corrCube[:, 0, :, 1] = 1; corrCube[:, 1, :, 1] = 1; corrCube[:, 2, :, 1] = 1; corrCube[:, 3, :, 1] = 1  # full horizontal (Q = 1)
    corrCube[:, 0, :, 2] = 1; corrCube[:, 1, :, 2] = 1j * 1; corrCube[:, 2, :, 2] = -1j * 1; corrCube[:, 3, :, 2] = 1  #full 45 linear (U = 1)
    stokesCube = conv.corrs2stokes(corrCube)
    assert np.allclose(stokesCube[0, :, 0, 0], np.array([1 + 0j, 0, 0, 1 + 0j]))
    assert np.allclose(stokesCube[0, :, 0, 1], np.array([1 + 0j, 1 + 0j, 0, 0]))
    assert np.allclose(stokesCube[0, :, 0, 2], np.array([1 + 0j, 0, 1 + 0j, 0]))

def testCubeTransformCorrs2StokesStokes():
    conv = ClassStokes([StokesTypes["I"], StokesTypes["Q"], StokesTypes["U"], StokesTypes["V"]],
                       "QVUI") #jumble the mapping and make sure things are mapped correctly
    corrCube = np.zeros([1,4,1,3],dtype=np.complex64)
    corrCube[:, 0, :, 0] = 1; corrCube[:, 1, :, 0] = 1;
    corrCube[:, 0, :, 1] = 2; corrCube[:, 2, :, 1] = 2;
    corrCube[:, 0, :, 2] = 3; corrCube[:, 3, :, 2] = 3;
    stokesCube = conv.corrs2stokes(corrCube)
    assert np.allclose(stokesCube[0, :, 0, 0], np.array([1+0j, 0, 0, 1+0j]))
    assert np.allclose(stokesCube[0, :, 0, 1], np.array([0, 0, 2+0j, 2+0j]))
    assert np.allclose(stokesCube[0, :, 0, 2], np.array([0, 3+0j, 0, 3+0j]))

def testCubeTransformStokes2CorrsLinear():
    conv = ClassStokes([StokesTypes["XX"], StokesTypes["XY"], StokesTypes["YX"], StokesTypes["YY"]],
                       "IQUV")
    stokesCube = np.zeros([1, 4, 1, 3], dtype=np.complex64)
    stokesCube[:, 0, :, 0] = 1; stokesCube[:, 1, :, 0] = 1; #full horizontal (Q=1)
    stokesCube[:, 0, :, 1] = 1; stokesCube[:, 2, :, 1] = 1; #full 45 linear (U=1)
    stokesCube[:, 0, :, 2] = 1; stokesCube[:, 3, :, 2] = 1; #full right circular (V=1)
    corrCube = conv.stokes2corrs(stokesCube)
    assert np.allclose(corrCube[0, :, 0, 0], np.array([2,0,0,0])) #I+Q=2 and I-Q=0
    assert np.allclose(corrCube[0, :, 0, 1], np.array([1,1,1,1])) #I+0=1 and U+0=1 and U-0=1 and I-0=0
    assert np.allclose(corrCube[0, :, 0, 2], np.array([1,1j,-1j,1])) #I+0=1 and 0+iV=1i and 0-iV=-1i and I-0=1

def testCubeTransformStokes2CorrsLinearNonStandardMSMapping():
    conv = ClassStokes([StokesTypes["XX"], StokesTypes["YY"], StokesTypes["XY"], StokesTypes["YX"]],
                       "IQUV")
    stokesCube = np.zeros([1, 4, 1, 3], dtype=np.complex64)
    stokesCube[:, 0, :, 0] = 1; stokesCube[:, 1, :, 0] = 1; #full horizontal (Q=1)
    stokesCube[:, 0, :, 1] = 1; stokesCube[:, 2, :, 1] = 0.25; stokesCube[:, 3, :, 1] = 0.75; #0.25 45 linear (U), 0.75 right circular (V)
    stokesCube[:, 0, :, 2] = 1; stokesCube[:, 3, :, 2] = 1; #full right circular (V=1)
    corrCube = conv.stokes2corrs(stokesCube)
    assert np.allclose(corrCube[0, :, 0, 0], np.array([2,0,0,0])) #I+Q=2 and I-Q=0
    assert np.allclose(corrCube[0, :, 0, 1], np.array([1,1,0.25+0.75j,0.25-0.75j])) #I+0=1 and I-0=1 and U+iV=0.75+0.25i and U-iV=0.75-0.25i
    assert np.allclose(corrCube[0, :, 0, 2], np.array([1,1,1j,-1j])) #I+0=1 and 0+iV=1i and 0-iV=-1i and I-0=1

def testCubeTransformStokes2CorrsCircular():
    conv = ClassStokes([StokesTypes["RR"], StokesTypes["RL"], StokesTypes["LR"], StokesTypes["LL"]],
                       "IQUV")
    stokesCube = np.zeros([1, 4, 1, 3], dtype=np.complex64)
    stokesCube[:, 0, :, 0] = 1; stokesCube[:, 1, :, 0] = 1; #full horizontal (Q=1)
    stokesCube[:, 0, :, 1] = 1; stokesCube[:, 2, :, 1] = 1; #full 45 linear (U=1)
    stokesCube[:, 0, :, 2] = 1; stokesCube[:, 3, :, 2] = 1; #full right circular (V=1)
    corrCube = conv.stokes2corrs(stokesCube)
    assert np.allclose(corrCube[0, :, 0, 0], np.array([1,1,1,1])) #I+0=1,Q+0=1,Q-0=1,I-0=1
    assert np.allclose(corrCube[0, :, 0, 1], np.array([1,1j,-1j,1])) #I+0=1,0+iU=1i,0-iU=-1i,I-0=1
    assert np.allclose(corrCube[0, :, 0, 2], np.array([2,0,0,0])) #I+V=2,I-V=0

def testCubeTransformStokes2CorrsStokes():
    conv = ClassStokes([StokesTypes["I"], StokesTypes["Q"], StokesTypes["U"], StokesTypes["V"]],
                       "QVUI") #jumble the mapping and make sure things are mapped correctly
    stokesCube = np.zeros([1,4,1,3],dtype=np.complex64)
    stokesCube[:, 3, :, 0] = 1; stokesCube[:, 1, :, 0] = 1;
    stokesCube[:, 1, :, 1] = 2; stokesCube[:, 2, :, 1] = 2;
    stokesCube[:, 0, :, 2] = 3; stokesCube[:, 3, :, 2] = 3;
    corrCube = conv.stokes2corrs(stokesCube)
    assert np.allclose(corrCube[0, :, 0, 0], np.array([1+0j, 0, 0, 1+0j]))
    assert np.allclose(corrCube[0, :, 0, 1], np.array([0, 0, 2+0j, 2+0j]))
    assert np.allclose(corrCube[0, :, 0, 2], np.array([3+0j, 3+0j, 0, 0]))

