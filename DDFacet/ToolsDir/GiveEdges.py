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

def GiveEdges((xc0,yc0),N0,(xc1,yc1),N1):
    M_xc=xc0
    M_yc=yc0
    NpixMain=N0
    F_xc=xc1
    F_yc=yc1
    NpixFacet=N1
    
    ## X
    M_x0=M_xc-NpixFacet/2
    x0main=np.max([0,M_x0])
    dx0=x0main-M_x0
    x0facet=dx0
    
    M_x1=M_xc+NpixFacet/2
    x1main=np.min([NpixMain-1,M_x1])
    dx1=M_x1-x1main
    x1facet=NpixFacet-dx1
    x1main+=1
    ## Y
    M_y0=M_yc-NpixFacet/2
    y0main=np.max([0,M_y0])
    dy0=y0main-M_y0
    y0facet=dy0
    
    M_y1=M_yc+NpixFacet/2
    y1main=np.min([NpixMain-1,M_y1])
    dy1=M_y1-y1main
    y1facet=NpixFacet-dy1
    y1main+=1
    
    Aedge=[x0main,x1main,y0main,y1main]
    Bedge=[x0facet,x1facet,y0facet,y1facet]
    return Aedge,Bedge
