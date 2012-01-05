from django.contrib.gis.db import models


class AbstractGeoManager(models.Model):
    objects = models.GeoManager()
    
    class Meta:
        abstract = True


class UserGeometryMetadata(AbstractGeoManager):
    """holds metadata for user-uploaded geometries"""
    code = models.CharField(max_length=50,unique=True,null=False,blank=False)
    desc = models.TextField()
    uid_field = models.CharField(max_length=50,null=False, blank=True)
    
    @property
    def geoms(self):
        '''Return a list of UserGeometryData objects'''
        return(self.usergeometrydata_set.model.objects.filter(user_meta=self.id))
    
    @property
    def geom_count(self):
        return(len(self.geoms))
    
    @property
    def vertex_count(self):
        '''Return a count of the vertices for all the geometries'''
        return [geom.geom.num_points for geom in self.geoms] 
    
    @property
    def vertex_count_total(self):
        '''Return a count of the vertices for all the geometries'''
        return sum(self.vertex_count)
    
    def geom_gmap_static_url(self,
        color = '0x0000ff',
        weight = 4,
        width = 512,
        height = 256,
    ):
        '''Returns a Google Maps Static API URL representation of the geometry
        
        Refs:
          http://code.google.com/apis/maps/documentation/staticmaps/#Paths
          http://en.wikipedia.org/wiki/Ramer%E2%80%93Douglas%E2%80%93Peucker_algorithm
        '''
        # estimate the simplification threshold based on the number of vertices
        
        if self.vertex_count_total < 10:
            threshold = 0  # no simplification
        elif self.vertex_count_total < 100:
            threshold = 0.01
        elif self.vertex_count_total < 1000:
            threshold = 0.1
        else:
            threshold = 0.5
        
        # construct the pathLocations string
        pathLocations='&'.join(
            [geom.pathLocations(color=color,weight=weight, threshold=threshold)
                for geom in self.geoms]
        )
        
        url = (
            'http://maps.googleapis.com/maps/api/staticmap'
            '?size={width}x{height}'
            '&sensor=false'
            '&{pathLocations}'
        ).format(
            color=color,
            weight=weight,
            pathLocations=pathLocations,
            width=width,
            height=height,
        )
        
        return url


class UserGeometryData(AbstractGeoManager):
    """holds user uploaded geometries"""
    gid = models.IntegerField(null=True)
    user_meta = models.ForeignKey(UserGeometryMetadata)
    desc = models.TextField(blank=True)
    geom = models.MultiPolygonField(srid=4326)

#    def _encode_polyline_data(polyline):
#        '''encode a polyline for Google Maps Static API
#        
#        Ref: 
#        http://code.google.com/apis/maps/documentation/utilities/polylinealgorithm.html
#        '''
#        
#        
#        
##        str = '|'.join( # join each vertex
##                        [','.join( #join each coordinate
##                            [str(coord) 
##                             for coord in tuple(reversed(vertex[:2]))
##                            ]
##                            ) for vertex in polygon
##                        ]
##                    )
#        str = ''.join( # join each vertex
#            [''.join( #join each coordinate
#                [coord * 1e5 
#                 for coord in tuple(reversed(vertex[:2]))
#                ]
#                ) for vertex in polyline
#            ]
#        )
#        
#        return 'dummy'
    
    def pathLocations(self,color='0x0000ff',weight=4, threshold=0.01):
        '''Returns a Google Maps Static API path Locations string for the geometry
        
        Note that only the first 2 dimensions of vertices are returned and they
        are ordered (lat,lon).
        
        If too many vertices are available, they will be simplified.
        
        Ref: http://code.google.com/apis/maps/documentation/staticmaps/#Paths
        '''
        from django.contrib.gis.geos import MultiPolygon
        from contrib.glineenc.glineenc import encode_pairs

        geom = self.geom
#        if geom.num_coords > 32:
#            geom = geom.simplify(0.1)
        
        #test = self.geom.simplify(0.01)
        #polygon=self.geom.coords[0][0]
        
#        if geom.geom_type == 'Polygon':
#            geom = MultiPolygon(geom)
        
        url = '&'.join( # join multiple multipolygons
            ['&'.join( # join multiple polygons
                ['path=color:{color}|weight:{weight}|enc:{encoded_data}'.format(
                    color=color,
                    weight=weight,
                    encoded_data=encode_pairs(
                        points=tuple([tuple(reversed(i)) for i in polygon]),
                        threshold=threshold,
                    )[0]
                 ) for polygon in multipolygon
                ]
             ) for multipolygon in geom.coords
            ]
        )
        return url


class NetcdfDataset(AbstractGeoManager):
    '''Models a netCDF4 Dataset object. Also a NC file anywhere.'''
    uri = models.TextField(unique=True)
    rowbnds_name = models.CharField(max_length=50)
    colbnds_name = models.CharField(max_length=50)
    time_name = models.CharField(max_length=50)
    time_units = models.CharField(max_length=100)
    calendar = models.CharField(max_length=50)
    spatial_extent = models.PolygonField(srid=4326)
    temporal_min = models.DateTimeField()
    temporal_max = models.DateTimeField()
    temporal_interval_days = models.FloatField()
    
    def __unicode__(self):
        return '{uri}'.format(uri=self.uri)


class NetcdfDatasetAttribute(AbstractGeoManager):
    '''stores key value pairs for NetCDF dataset global attributes'''
    netcdf_dataset  = models.ForeignKey(NetcdfDataset)
    key             = models.CharField(max_length=50)
    value           = models.TextField()
    
    class Meta():
        unique_together = ('netcdf_dataset','key')


class NetcdfDimension(AbstractGeoManager):
    '''Models the dimension of a NetCDF dataset'''
    netcdf_dataset = models.ForeignKey(NetcdfDataset)
    name           = models.CharField(max_length=50)
    size           = models.IntegerField()
    
    class Meta():
        unique_together = ('netcdf_dataset','name')
    
    def __unicode__(self):
        return '{name} (size={size})'.format(name=self.name,size=self.size)

class NetcdfDimensionAttribute(AbstractGeoManager):
    '''stores key value pairs for NetCDF dimension attributes'''
    netcdf_dimension = models.ForeignKey(NetcdfDimension)
    key              = models.CharField(max_length=50)
    value            = models.TextField()
    
    class Meta():
        unique_together = ('netcdf_dimension','key')


class NetcdfVariable(AbstractGeoManager):
    '''Models an abstract NetCDF dataset variable
    '''
    netcdf_dataset = models.ForeignKey(NetcdfDataset)
    code           = models.CharField(max_length=255)
    ndim           = models.IntegerField()
    
    class Meta():
        unique_together = ('netcdf_dataset','code')
    
    def __unicode__(self):
        return "{code} (dimensions={ndim})".format(code=self.code, ndim=self.ndim)


class NetcdfVariableAttribute(AbstractGeoManager):
    '''stores key value pairs for NetCDF variable attributes'''
    netcdf_variable = models.ForeignKey(NetcdfVariable)
    key             = models.CharField(max_length=50)
    value           = models.TextField()
    
    class Meta():
        unique_together = ('netcdf_variable','key')


class NetcdfVariableDimension(AbstractGeoManager):
    '''Models the dimension of a NetCDF Variable'''
    netcdf_variable  = models.ForeignKey(NetcdfVariable)
    netcdf_dimension = models.ForeignKey(NetcdfDimension)
    position = models.IntegerField()
    
    class Meta():
        unique_together = ('netcdf_variable','netcdf_dimension')
    
    def __unicode__(self):
        return "{var} {dim} ({position})".format(
            var=self.variable, 
            dim=self.code,
            position=self.position,
        )


class Organization(AbstractGeoManager):
    '''Models an organization (that has a climate model)
    
    Example: National Center for Atmospheric Research (ncar) 
    '''
    name          = models.CharField(max_length=255)
    code          = models.CharField(max_length=25, unique=True)
    country       = models.CharField(max_length=255)
    url           = models.URLField(
        verify_exists=False, 
        max_length=200,
        null=True,
        unique=True,
    )
    
    def __unicode__(self):
        return "{name} ({code})".format(name=self.name, code=self.code)


class Scenario(AbstractGeoManager):
    '''A climate model emissions scenario
    
    Example: 2xCO2 equilibrium experiment (2xCO2)
    Reference: http://www-pcmdi.llnl.gov/ipcc/standard_output.html#Experiments
    '''
    name          = models.CharField(max_length=50)
    code          = models.CharField(max_length=10, unique=True)
    urlslug       = models.CharField(max_length=10, unique=True)
    description   = models.TextField(null=True)
    
    class Meta():
        verbose_name = "climate emissions scenario"
    
    def __unicode__(self):
        return "{code}".format(code=self.code)


class ScenarioMetadataUrl(AbstractGeoManager):
    '''Models the URL of a Emissions Scenario metadata webpage'''
    scenario = models.ForeignKey(Scenario)
    url      = models.URLField(
        verify_exists=False, 
        max_length=200,
    )
    desc     = models.TextField()
    
    def __unicode__(self):
        return(self.url)


class Archive(AbstractGeoManager):
    '''Models an climate model data archive
    
    Example: Coupled Model Intercomparison Project (CMIP3) 
    '''
    name          = models.CharField(max_length=255, unique=True)
    code          = models.CharField(max_length=25, unique=True)
    urlslug       = models.CharField(max_length=25, unique=True)
    url           = models.URLField(
        verify_exists=False, 
        max_length=200,
        null=True,
        unique=True,
    )
    
    class Meta():
        verbose_name = "climate simulation archive"
    
    def __unicode__(self):
        return "{code}".format(code=self.code)


class ArchiveMetadataUrl(AbstractGeoManager):
    '''Models the URL of a Archive metadata webpage'''
    archive = models.ForeignKey(Archive)
    url      = models.URLField(
        verify_exists=False, 
        max_length=200,
    )
    desc     = models.TextField()
    
    def __unicode__(self):
        return(self.url)


class ClimateModel(AbstractGeoManager):
    '''A climate model
    
    Example: Community Climate System Model, version 3.0 (CCSM3)
    Reference: http://www-pcmdi.llnl.gov/ipcc/model_documentation/ipcc_model_documentation.php
    '''
    name          = models.CharField(max_length=50)
    code          = models.CharField(max_length=25, unique=True)
    urlslug       = models.CharField(max_length=25, unique=True)
    organization  = models.ForeignKey(Organization)
    comments      = models.TextField(null=False, blank=True)
    
    class Meta():
        verbose_name = "climate model"
    
    def __unicode__(self):
        return "{code}".format(code=self.code)


class ClimateModelMetadataUrl(AbstractGeoManager):
    '''Models the URL of a Climate Model metadata webpage'''
    model    = models.ForeignKey(ClimateModel)
    url      = models.URLField(
        verify_exists=False, 
        max_length=200,
    )
    desc     = models.TextField()
    
    def __unicode__(self):
        return(self.url)


class Variable(AbstractGeoManager):
    '''Models an climate model variable
    
    Example: air_temperature (tas)
    
    Ref: http://www-pcmdi.llnl.gov/ipcc/standard_output.html#Highest_priority_output
    '''
    code         = models.CharField(max_length=25, unique=True)
    urlslug      = models.CharField(max_length=25, unique=True)
    name         = models.CharField(max_length=50)
    units        = models.CharField(max_length=25)
    ndim         = models.IntegerField()
    description  = models.TextField(null=True)
    
    class Meta():
        verbose_name = "climate simulation variable"
    
    def __unicode__(self):
        return "{name} ({code})".format(name=self.name, code=self.code)


class VariableMetadataUrl(AbstractGeoManager):
    '''Models the URL of a Climate Model metadata webpage'''
    variable = models.ForeignKey(Variable)
    url      = models.URLField(
        verify_exists=False, 
        max_length=200,
    )
    desc     = models.TextField()
    
    def __unicode__(self):
        return(self.url)


class SimulationOutput(AbstractGeoManager):
    '''Models climate model output datasets'''
    
    archive         = models.ForeignKey(Archive)
    scenario        = models.ForeignKey(Scenario)
    climate_model   = models.ForeignKey(ClimateModel)
    variable        = models.ForeignKey(Variable)
    run             = models.IntegerField()
    netcdf_variable = models.ForeignKey(NetcdfVariable)
    
    class Meta():
        unique_together = ('archive','scenario','climate_model','variable','run')
        verbose_name = "climate simulation output"
    
    def __unicode__(self):
        return '{archive}:{scenario}:{model}:{variable}'.format(
            archive=self.archive,
            scenario=self.scenario,
            model=self.climate_model,
            variable=self.netcdf_variable.code,
        )
