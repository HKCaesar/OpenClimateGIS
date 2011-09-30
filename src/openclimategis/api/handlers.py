from piston.handler import BaseHandler
from emitters import *
from piston.utils import rc
from util.helpers import parse_polygon_wkt, merge_dict
from django.contrib.gis.geos.geometry import GEOSGeometry
import datetime
from climatedata import models
import inspect
from util.raw_sql import get_dataset, execute
import netCDF4
from slug import *
import climatedata.models
from experimental.in_memory_oo_update import OcgDataset
from util.ncconv.in_memory_oo_multi_core import multipolygon_multicore_operation


class ocg(object):
    """Structure class to hold keyword arguments."""
    
    def __repr__(self):
        prints = []
        mems = inspect.getmembers(self)
        for mem in mems:
            if not mem[0].startswith('__'):
                prints.append('{0}={1}\n'.format(*mem))
        return(''.join(prints))

class OpenClimateHandler(BaseHandler):
    """Superclass for all OpenClimate handlers."""
    
    allowed_methods = ('GET',)
    
    def __init__(self,*args,**kwds):
        ## set some default parameters for the handlers
        self.ocg = ocg()
        
        super(OpenClimateHandler,self).__init__(*args,**kwds)
    
    def read(self,request,**kwds):
        """
        Subclasses should not overload this method. Each return will be checked
        for basic validity.
        """
#        import ipdb;ipdb.set_trace()
        ## parse query
#        self._query_string_(request)
        ## parse URL arguments
        self._parse_slugs_(kwds)
        ## add OCG object to request object for use by emitters
        request.ocg = self.ocg
#        import ipdb;ipdb.set_trace()
        ## call the subclass read methods
        return self.check(self._read_(request))
    
    def check(self,payload):
        """Basic checks on returned data."""
        
        if len(payload) == 0:
            return rc.NOT_FOUND
        else:
            return payload
        
    def _read_(self,request,**kwds):
        """Overload in subclasses."""
        
        raise NotImplementedError
    
    def _parse_slugs_(self,kwds):
        
        self.ocg.temporal = TemporalSlug('temporal',possible=kwds).value
        self.ocg.aoi = PolygonSlug('aoi',possible=kwds).value
        self.ocg.aggregate = AggregateSlug('aggregate',possible=kwds).value
        self.ocg.operation = OperationSlug('operation',possible=kwds).value
        self.ocg.html_template = OcgSlug('html_template',possible=kwds).value
        self.ocg.run = IntegerSlug('run',possible=kwds).value
        
        self.ocg.variable = IExactQuerySlug(models.Variable,'variable',possible=kwds,one=True).value
        self.ocg.scenario = IExactQuerySlug(models.Scenario,'scenario',possible=kwds,one=True).value
        self.ocg.archive = IExactQuerySlug(models.Archive,'archive',possible=kwds,one=True).value
        self.ocg.climate_model = IExactQuerySlug(models.ClimateModel,'model',possible=kwds,one=True).value
        
        ## return the dataset object if all components passed
        if all([self.ocg.scenario,self.ocg.archive,self.ocg.climate_model,self.ocg.run,self.ocg.variable]):
            fkwds = dict(archive=self.ocg.archive,
                         scenario=self.ocg.scenario,
                         climate_model=self.ocg.climate_model,
                         run=self.ocg.run,
                         variable=self.ocg.variable)
            qs = climatedata.models.SimulationOutput.objects.filter(**fkwds)
            assert(len(qs) == 1)
            self.ocg.simulation_output = qs[0]
        else:
            self.ocg.simulation_output = None
            
#        import ipdb;ipdb.set_trace()
            
        
    
#    def _parse_kwds_(self,kwds):
#        """Parser and formatter for potential URL keyword arguments."""
#        
#        def _format_date_(start,end):
#            return([datetime.datetime.strptime(d,'%Y-%m-%d') for d in [start,end]])
#        def _get_iexact_(model,code):
##            if code == 'ps': import ipdb;ipdb.set_trace()
#            "Return a single record from the database. Otherwise raise exception."
#            ## this is the null case and should be treated as such
#            if code == None:
#                ret = None
#            else:
#                obj = model.objects.filter(code__iexact=code)
#                if len(obj) != 1:
#                    obj = model.objects.filter(name__iexact=code)
#                    if len(obj) != 1:
#                        msg = '{0} records returned for model {1} with code query {2}'.format(len(obj),model,code)
#                        raise ValueError(msg)
#                    else:
#                        ret = obj[0]
#                else:
#                    ret = obj[0]
#            return(ret)
#        
#        ## name of the scenario
#        self.ocg.scenario = kwds.get('scenario')
#        ## the temporal arguments
#        t = kwds.get('temporal')
#        if t != None:
#            if '+' in t:
#                start,end = t.split('+')
#            else:
#                start = t
#                end = t
#                self.ocg.temporal = _format_date_(start,end)
#        else:
#            self.ocg.temporal = None
#        ## the polygon overlay
#        aoi = kwds.get('aoi')
#        if aoi:
#            self.ocg.aoi = GEOSGeometry(parse_polygon_wkt(aoi))
#        else:
#            self.ocg.aoi = None
#        ## the model archive
#        self.ocg.archive = kwds.get('archive')
#        ## target variable
#        self.ocg.variable = kwds.get('variable')
#        ## aggregation boolean
#        agg = kwds.get('aggregate')
#        ## the None case is different than 'true' or 'false'
#        if agg:
#            if agg.lower() == 'true':
#                self.ocg.aggregate = True
#            elif agg.lower() == 'false':
#                self.ocg.aggregate = False
#            else:
#                msg = '"{0}" aggregating boolean operation not recognized.'
#                raise(ValueError(msg.format(agg)))
#        else:
#            self.ocg.aggregate = None
#        ## the model designation
#        self.ocg.model = kwds.get('model')
#        ## the overlay operation
#        self.ocg.operation = kwds.get('operation')
#        
#        ## these queries return objects from the database classifying the NetCDF.
#        ## the goal is to return the prediction.
#        if self.ocg.archive:
#            self.ocg.archive_obj = _get_iexact_(models.Archive,self.ocg.archive)
#            self.ocg.climatemodel_obj = models.ClimateModel.objects.filter(archive=self.ocg.archive_obj,
#                                                                           code__iexact=self.ocg.model)[0]
##        self.ocg.climatemodel_obj = _get_iexact_(models.ClimateModel,self.ocg.model)
##        self.ocg.scenario_obj = _get_iexact_(models.Scenario,self.ocg.scenario)
##        self.ocg.variable_obj = _get_iexact_(models.Variable,self.ocg.variable)
#        ## if we have data for each component, we can return a prediction
#        if all([self.ocg.archive,self.ocg.model,self.ocg.scenario,self.ocg.variable,self.ocg.temporal]):
#            ## execute the raw sql select statement to return the dataset(s)
#            sql = get_dataset(self.ocg.archive_obj.id,
#                              self.ocg.variable,
#                              self.ocg.scenario,
#                              self.ocg.temporal,
#                              self.ocg.climatemodel_obj.code)
#            rows = execute(sql)
#            ## return the dataset object(s)
##            if len(rows) > 1:
#            pks = [ii[0] for ii in rows]
#            self.ocg.dataset_obj = models.Dataset.objects.filter(pk__in=pks)
#            
#            
##            else:
##                self.ocg.dataset_obj = [models.Dataset.objects.filter(pk=rows[0][0])[0]]
#            
##            ## return potential climate models from the archive selection
##            cms = ClimateModel.objects.filter(archive=self.ocg.archive_obj)
##            ## find potential datasets
##            datasets = Dataset.objects.filter(climatemodel__in=cms,
##                                              scenario=self.ocg.scenario_obj)
##            ## filter by variable
##            var_dataset_ids = Variable.objects.filter()
##            ## narrow down the search by looking through the time data
##            dataset = IndexTime.objects.filter(dataset__in=datasets,
##                                                  value__range=self.ocg.temporal).\
##                                           values('dataset').\
##                                           distinct()
##            import ipdb;ipdb.set_trace()
##            fkwds = dict(archive=self.ocg.archive_obj,
##                         climate_model=self.ocg.model_obj,
##                         experiment=self.ocg.scenario_obj,
##                         variable=self.ocg.variable_obj)
##            self.ocg.prediction_obj = models.Prediction.objects.filter(**fkwds)
##            if len(self.ocg.prediction_obj) != 1:
##                raise ValueError('prediction query should return 1 record.')
##            self.ocg.prediction_obj = self.ocg.prediction_obj[0]
#        else:
#            self.ocg.dataset_obj = None


class NonSpatialHandler(OpenClimateHandler):
    __data_kwds__ = {}
     
    def _read_(self,request,code=None):
        if code:
            query = self.model.objects.filter(code__iexact=str(code))
        else:
            query = self.model.objects.all()
        return query


#class ArchiveHandler(NonSpatialHandler):
#    model = Archive
#    
#    
#class ClimateModelHandler(NonSpatialHandler):
#    model = ClimateModel
#    
#    
#class ExperimentHandler(NonSpatialHandler):
#    model = Scenario
#    
#    
#class VariableHandler(NonSpatialHandler):
#    model = Variable
    
    
class SpatialHandler(OpenClimateHandler):
    
    def _read_(self,request):
        
#        import ipdb;ipdb.set_trace()
        
        dataset = self.ocg.simulation_output.netcdf_variable.netcdf_dataset
        
        ## arguments for the dataset object
        kwds = dict(rowbnds_name=dataset.rowbnds_name,
                    colbnds_name=dataset.colbnds_name,
                    time_name=dataset.time_name,
                    time_units=dataset.time_units,
                    calendar=dataset.calendar,)
#                    level_name=self.ocg.dataset.level_name,) TODO: add level variable name

        ## construct arguments to clip operation
        if self.ocg.operation == 'clip':
            clip = True
        else:
            clip = False

#        import ipdb;ipdb.set_trace()
        
        elements = multipolygon_multicore_operation(dataset.uri,
                                      self.ocg.simulation_output.netcdf_variable.code,
                                      [self.ocg.aoi],
                                      time_range=self.ocg.temporal,
                                      clip=clip,
                                      dissolve=self.ocg.aggregate,
                                      levels=None,
                                      ocgOpts=kwds,
                                      subdivide=True,
                                      #subres = 90
                                      )
        
#        import ipdb;ipdb.set_trace()
        
#        try:
#            dataset = netCDF4.Dataset(self.ocg.dataset.uri,'r')
#            d = OcgDataset(dataset,**kwds)
#            ## pull the elements
#            elements = d.extract_elements(self.ocg.variable.title(), # TODO: variable formatting
#                                          dissolve=self.ocg.aggregate,
#                                          polygon=self.ocg.aoi,
#                                          time_range=self.ocg.temporal,
#                                          clip=self.ocg.operation)
#        ## close the connection...
#        finally:
#            dataset.close()
            
        return(elements)
        
#        self.rowbnds_name = kwds.get('rowbnds_name') or 'bounds_latitude'
#        self.colbnds_name = kwds.get('colbnds_name') or 'bounds_longitude'
#        self.time_name = kwds.get('time_name') or 'time'
#        self.time_units = kwds.get('time_units') or 'days since 1950-01-01 00:00:00'
#        self.calendar = kwds.get('calendar') or 'proleptic_gregorian'
#        self.level_name = kwds.get('level_name') or 'levels'
        
#        return(climatedata.models.Dataset.objects.all())
        
#        from tests import get_example_netcdf
#        
#        attrs = get_example_netcdf()
        
#        ## SPATIAL QUERYING ----------------------------------------------------
#        
#        ocgeom = OpenClimateGeometry(self.ocg.climatemodel_obj,
#                                     self.ocg.aoi,
#                                     self.ocg.operation,
#                                     self.ocg.aggregate)
#        geom_list = ocgeom.get_geom_list()
#        row,col = ocgeom.get_indices()
#        weights = ocgeom.get_weights()
#        
#        ## it is possible that multiple datasets are returned by a query. this
#        ## occurs when a temporal range overlaps multiple datasets. hence, we 
#        ## always put the retrieval in a loop.
#        
#        for ii,dataset in enumerate(self.ocg.dataset_obj):
#        
#            ## TEMPORAL QUERYING -----------------------------------------------
#            
#            ti = IndexTime.objects.filter(dataset=dataset)\
#                                  .filter(value__range=self.ocg.temporal)
#            ti = ti.order_by('index').values_list('index',flat=True)
#    
#            ## RETRIEVE NETCDF DATA --------------------------------------------
#            
#            rootgrp = netCDF4.Dataset(dataset.uri,'r')
#            try:
#                na = NetCdfAccessor(rootgrp,self.ocg.variable)
#                ## extract a dictionary representation of the netcdf
#                dl = na.get_dict(geom_list,
#                                 time_indices=ti,
#                                 row=row,
#                                 col=col,
#                                 aggregate=self.ocg.aggregate,
#                                 weights=weights)
#                ## append the data
#                if ii == 0:
#                    dls = dl
#                else:
#                    dls += dl
#            finally:
#                rootgrp.close()
#        
#        return(dls)
    
    
#class OpenClimateGeometry(object):
#    """
#    Perform OpenClimateGIS geometry operations. Manages clip v. intersect
#    operations and spatial unioning in the case of an aggregation.
#    
#    aoi -- GEOSGeometry Polygon object acting as the geometric selection overlay.
#    op -- 'intersect(s)' or 'clip'
#    aggregate -- set to True to union the geometries.
#    """
#    
#    def __init__(self,climatemodel,aoi,op,aggregate):
#        self.aoi = aoi
#        self.op = op
#        self.aggregate = aggregate
#        self.climatemodel = climatemodel
#        
#        self.__qs = None ## queryset with correct spatial operations
#        self.__geoms = None ## list of geometries with correct attribute selected
#        
#        ## set the geometry attribute depending on the operation
#        if op in ['intersect','intersects']:
#            self._gattr = 'geom'
#        elif op == 'clip':
#            self._gattr = 'intersection'
#        else:
#            msg = 'spatial operation "{0}" not recognized.'.format(op)
#            raise NotImplementedError(msg)
#                                          
#    def get_indices(self):
#        "Returning row and column indices used to index into NetCDF."
#        
#        row = [obj.row for obj in self._qs]
#        col = [obj.col for obj in self._qs]
#        return((row,col))
#    
#    def get_weights(self):
#        "Returns weights for each polygon in the case of an aggregation."
#        
##        if self.aggregate:
#            ## calculate weights for each polygon
#        areas = [obj.area for obj in self._geoms]
#        asum = sum(areas)
#        weights = [a/asum for a in areas]
#        weights = [dict(weight=w,row=obj.row,col=obj.col) for w,obj in zip(weights,self._qs)]
##            weights = dict(zip(weights,
##                               [dict(row=obj.row,col=obj.col) for obj in self._qs]))
##            import ipdb;ipdb.set_trace()
##            ret = weights
##        else:
##            ret = None
#        return(weights)
#    
#    def get_geom_list(self):
#        "Return the list of geometries accounting for processing parms."
#        
#        if self.aggregate:
#            ret = self._union_geoms_()
#        else:
#            ret = self._geoms
#        return(ret)
#    
#    @property
#    def _qs(self):
#        if self.__qs == None:
#            ## always perform the spatial select to limit returned records.
#            self.__qs = IndexSpatial.objects.filter(climatemodel=self.climatemodel,
#                                                    geom__intersects=self.aoi)\
#                                            .order_by('row','col')
#            ## intersection operations require element-by-element intersection
#            ## operations.
#            if self.op == 'clip':
#                self.__qs = self.__qs.intersection(self.aoi)
#        return(self.__qs)
#    
#    @property
#    def _geoms(self):
#        if self.__geoms == None:
#            self.__geoms = [getattr(obj,self._gattr) for obj in self._qs]
#        return(self.__geoms)
#    
#    def _union_geoms_(self):
#        "Returns the union of geometries in the case of an aggregation."
#        
#        first = True
#        for geom in self._geoms:
#            if first:
#                union = geom
#                first = False
#            else:
#                union = union.union(geom)
#        return(union)
