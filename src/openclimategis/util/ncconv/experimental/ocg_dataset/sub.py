import util.ncconv.experimental.ploader as pl
import numpy as np
from shapely.geometry.multipolygon import MultiPolygon
import copy
from util.ncconv.experimental.helpers import timing, get_sr, get_area, keep,\
    union_sum
import itertools
from shapely import prepared
from shapely.ops import cascaded_union
from util.helpers import get_temp_path
from sqlalchemy.pool import NullPool
from shapely.geometry.polygon import Polygon


class SubOcgDataset(object):
    __attrs__ = ['geometry','value','gid','weight','timevec','levelvec']
    
    def __init__(self,geometry,value,timevec,gid=None,levelvec=None,mask=None,id=None):
        """
        geometry -- numpy array with dimension (n) of shapely Polygon 
            objects
        value -- numpy array with dimension (time,level,n)
        gid -- numpy array containing integer unique ids for the grid cells.
            has dimension (n)
        timevec -- numpy array with indices corresponding to time dimension of
            value
        mask -- boolean mask array with same dimension as value. will subset other
            inputs if passed. a value to be masked is indicated by True.
        """
        
        self.id = id
        self.geometry = np.array(geometry)
        self.value = np.array(value)
        self.timevec = np.array(timevec)
        
        if gid is not None:
            self.gid = np.array(gid)
        else:
            self.gid = np.arange(1,len(self.geometry) + 1)
        if levelvec is not None:
            self.levelvec = np.array(levelvec)
        else:
            if len(self.value) == 0:
                self.levelvec = np.array()
            else:
                self.levelvec = np.arange(1,self.value.shape[1]+1)
        
        ## if the mask is passed, subset the data
        if mask is not None:
            mask = np.invert(mask)[0,0,:]
            self.geometry = self.geometry[mask]
            self.gid = self.gid[mask]
            self.value = self.value[:,:,mask]
        
        ## calculate nominal weights
        self.weight = np.ones(self.geometry.shape,dtype=float)
        
    def to_grid_dict(self,ocg_dataset):
        """assumes an intersects-like operation with no union"""
        ## make the bounding polygon
        envelope = MultiPolygon(self.geometry.tolist()).envelope
        ## get the x,y vectors
        x,y = ocg_dataset.spatial.subset_centroids(envelope)
        ## make the grids
        gx,gy = np.meshgrid(x,y)
        ## make the empty boolean array
        mask = np.empty((self.value.shape[0],
                        self.value.shape[1],
                        gx.shape[0],
                        gx.shape[1]),dtype=bool)
        mask[:,:,:,:] = True
        ## make the empty geometry id
        gidx = np.empty(gx.shape,dtype=int)
        gidx = np.ma.array(gidx,mask=mask[0,0,:,:])
        ## make the empty value array
#        value = np.empty(mask.shape,dtype=float)
        ## loop for each centroid
        for ii,geom in enumerate(self.geometry):
            diffx = abs(gx - geom.centroid.x)
            diffy = abs(gy - geom.centroid.y)
            diff = diffx + diffy
            idx = diff == diff.min()
            mask[:,:,idx] = False
            gidx[idx] = ii
#            for dt in self.dim_time:
#                for dl in self.dim_level:
#                    value[dt,dl,idx] = self.value[dt,dl,ii]
        # construct the masked array
#        value = np.ma.array(value,mask=mask,fill_value=fill_value)
        ## if level is not included, squeeze out the dimension
#        if not include_level:
#            value = value.squeeze()
#        ## construct row and column bounds
#        xbnds = np.empty((len(self.geometry),2),dtype=float)
#        ybnds = xbnds.copy()
        ## subset the bounds
        xbnds,ybnds = ocg_dataset.spatial.subset_bounds(envelope)
        ## put the data together
        ret = dict(xbnds=xbnds,ybnds=ybnds,x=x,y=y,mask=mask,gidx=gidx)
        return(ret)
        
    def copy(self,**kwds):
        new_ds = copy.copy(self)
        def _find_set(kwd):
            val = kwds.get(kwd)
            if val is not None:
                setattr(new_ds,kwd,val) 
        for attr in self.__attrs__:  _find_set(attr)  
        return(new_ds)
    
    def merge(self,sub,id=None):
        """Assumes same time and level vectors."""
        geometry = np.hstack((self.geometry,sub.geometry))
        value = np.dstack((self.value,sub.value))
        gid = np.hstack((self.gid,sub.gid))
        ## if there are non-unique cell ids (which may happen with union
        ## operations, regenerate the unique values.
        if len(gid) > len(np.unique(gid)):
            gid = np.arange(1,len(gid)+1)
        return(self.copy(geometry=geometry,
                         value=value,
                         gid=gid,
                         id=id))
    
    @timing 
    def purge(self):
        """looks for duplicate geometries"""
        unique,uidx = np.unique([geom.wkb for geom in self.geometry],return_index=True)
        self.geometry = self.geometry[uidx]
        self.gid = self.gid[uidx]
        self.value = self.value[:,:,uidx]
        
        
    def __iter__(self):
        for dt,dl,dd in itertools.product(self.dim_time,self.dim_level,self.dim_data):
            d = dict(geometry=self.geometry[dd],
                     value=float(self.value[dt,dl,dd]),
                     time=self.timevec[dt],
                     level=int(self.levelvec[dl]),
                     gid=int(self.gid[dd]))
            yield(d)
            
    def iter_with_area(self,area_srid=3005):
        sr_orig = get_sr(4326)
        sr_dest = get_sr(area_srid)
        for attrs in self:
            attrs.update(dict(area_m2=get_area(attrs['geometry'],sr_orig,sr_dest)))
            yield(attrs)
    
    def _range_(self,idx):
        try:
            return(range(self.value.shape[idx]))
        except IndexError:
            return([])
    
    @property
    def dim_time(self):
        return(self._range_(0))

    @property
    def dim_level(self):
        return(self._range_(1))

    @property
    def dim_data(self):
        return(self._range_(2))
                     
    @property
    def area(self):
        area = 0.0
        for geom in self.geometry:
            area += geom.area
        return(area)
        
    def clip(self,igeom):
        prep_igeom = prepared.prep(igeom)
        for ii,geom in enumerate(self.geometry):
            if keep(prep_igeom,igeom,geom):
                new_geom = igeom.intersection(geom)
                weight = new_geom.area/geom.area
                assert(weight != 0.0) #tdk
                self.weight[ii] = weight
                self.geometry[ii] = new_geom
        
    def report_shape(self):
        for attr in self.__attrs__:
            rattr = getattr(self,attr)
            msg = '{0}={1}'.format(attr,getattr(rattr,'shape'))
            print(msg)
        
    def union(self):
        self._union_geom_()
        self._union_sum_()
        
    def union_nosum(self):
        self._union_geom_()
        
    def _union_geom_(self):
        ## union the geometry. just using np.array() on a multipolgon object
        ## results in a (1,n) array of polygons.
        new_geometry = np.array([None],dtype=object)
        new_geometry[0] = cascaded_union(self.geometry)
        self.geometry = new_geometry
        
    def _union_sum_(self):
        self.value = union_sum(self.weight,self.value,normalize=True)
        self.gid = np.array([1])
    
    @timing
    def as_sqlite(self,add_area=True,
                       area_srid=3005,
                       wkt=True,
                       wkb=False,
                       as_multi=True,
                       to_disk=False,
                       procs=1):
        from sqlalchemy import create_engine
        from sqlalchemy.orm.session import sessionmaker
        import db
        
        path = 'sqlite://'
        if to_disk or procs > 1:
            path = path + '/' + get_temp_path('.sqlite',nest=True)
            db.engine = create_engine(path,
                                      poolclass=NullPool)
        else:
            db.engine = create_engine(path,
#                                      connect_args={'check_same_thread':False},
#                                      poolclass=StaticPool
                                      )
        db.metadata.bind = db.engine
        db.Session = sessionmaker(bind=db.engine)
        db.metadata.create_all()

        print('  loading geometry...')
        ## spatial reference for area calculation
        sr = get_sr(4326)
        sr2 = get_sr(area_srid)

#        data = dict([[key,list()] for key in ['gid','wkt','wkb','area_m2']])
#        for dd in self.dim_data:
#            data['gid'].append(int(self.gid[dd]))
#            geom = self.geometry[dd]
#            if isinstance(geom,Polygon):
#                geom = MultiPolygon([geom])
#            if wkt:
#                wkt = str(geom.wkt)
#            else:
#                wkt = None
#            data['wkt'].append(wkt)
#            if wkb:
#                wkb = str(geom.wkb)
#            else:
#                wkb = None
#            data['wkb'].append(wkb)
#            data['area_m2'].append(get_area(geom,sr,sr2))
#        self.load_parallel(db.Geometry,data,procs)

        def f(idx,geometry=self.geometry,gid=self.gid,wkt=wkt,wkb=wkb,sr=sr,sr2=sr2,get_area=get_area):
            geom = geometry[idx]
            if isinstance(geom,Polygon):
                geom = MultiPolygon([geom])
            if wkt:
                wkt = str(geom.wkt)
            else:
                wkt = None
            if wkb:
                wkb = str(geom.wkb)
            else:
                wkb = None
            return(dict(gid=int(gid[idx]),
                        wkt=wkt,
                        wkb=wkb,
                        area_m2=get_area(geom,sr,sr2)))
        fkwds = dict(geometry=self.geometry,gid=self.gid,wkt=wkt,wkb=wkb,sr=sr,sr2=sr2,get_area=get_area)
        gen = pl.ParallelGenerator(db.Geometry,self.dim_data,f,fkwds=fkwds,procs=procs)
        gen.load()

        print('  loading time...')
        ## load the time data
        data = dict([[key,list()] for key in ['tid','time','day','month','year']])
        for ii,dt in enumerate(self.dim_time,start=1):
            data['tid'].append(ii)
            data['time'].append(self.timevec[dt])
            data['day'].append(self.timevec[dt].day)
            data['month'].append(self.timevec[dt].month)
            data['year'].append(self.timevec[dt].year)
        self.load_parallel(db.Time,data,procs)
            
        print('  loading value...')
        ## set up parallel loading data
        data = dict([key,list()] for key in ['gid','level','tid','value'])
        for ii,dt in enumerate(self.dim_time,start=1):
            for dl in self.dim_level:
                for dd in self.dim_data:
                    data['gid'].append(int(self.gid[dd]))
                    data['level'].append(int(self.levelvec[dl]))
                    data['tid'].append(ii)
                    data['value'].append(float(self.value[dt,dl,dd]))
        self.load_parallel(db.Value,data,procs)

        return(db)
    
    def load_parallel(self,Model,data,procs):
        pmodel = pl.ParallelModel(Model,data)
        ploader = pl.ParallelLoader(procs=procs)
        ploader.load_model(pmodel)
    
    def display(self,show=True,overlays=None):
        import matplotlib.pyplot as plt
        from descartes.patch import PolygonPatch
        
        ax = plt.axes()
        x = []
        y = []
        for geom in self.geometry:
            if isinstance(geom,MultiPolygon):
                for geom2 in geom:
                    try:
                        ax.add_patch(PolygonPatch(geom2,alpha=0.5))
                    except:
                        geom2 = wkt.loads(geom2.wkt)
                        ax.add_patch(PolygonPatch(geom2,alpha=0.5))
                    ct = geom2.centroid
                    x.append(ct.x)
                    y.append(ct.y)
            else:
                ax.add_patch(PolygonPatch(geom,alpha=0.5))
                ct = geom.centroid
                x.append(ct.x)
                y.append(ct.y)
        if overlays is not None:
            for geom in overlays:
                ax.add_patch(PolygonPatch(geom,alpha=0.5,fc='#999999'))
        ax.scatter(x,y,alpha=1.0)
        if show: plt.show()