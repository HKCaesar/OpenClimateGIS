from piston.emitters import Emitter
from django.http import HttpResponse
from util.shapes.views.export import ShpResponder
from util.toshp import OpenClimateShp
from util.helpers import get_temp_path


class OpenClimateEmitter(Emitter):
    """
    Superclass for all OpenClimateGIS emitters.
    """
    def render(self,request):
        raise NotImplementedError
    
class GeometryEmitter(OpenClimateEmitter):
    
    def construct(self):
        return self.data
    
#    def construct(self):
#        import ipdb;ipdb.set_trace()
    

class HelloWorldEmitter(OpenClimateEmitter):
    
    def render(self,request):
        names = [n['name'] for n in self.construct()]
        msg = 'Hello, World!! The climate model names are:<br><br>{0}'.format('<br>'.join(names))
        return HttpResponse(msg)
    
    
class HtmlEmitter(OpenClimateEmitter):
    
    def render(self,request):
        return HttpResponse(str(self.construct()))

   
class ShapefileEmitter(GeometryEmitter):
    """
    Emits zipped shapefile (.shz)
    """
    
    def render(self,request):
        dl = self.construct()
        path = get_temp_path(suffix='.shp')
#        import ipdb;ipdb.set_trace()
        shp = OpenClimateShp(path,dl)
        shp.write()
        return shp.zip_response()
    
    
class KmlEmitter(OpenClimateEmitter):
    """
    Emits raw KML (.kml)
    """

    def render(self,request):
        pass
    
    
class KmzEmitter(KmlEmitter):
    """
    Subclass of KmlEmitter. Emits KML in a zipped format (.kmz)
    """
    
    def render(self,request):
        kml = super(KmzEmitter,self).render()
        
        
class GeoJsonEmitter(OpenClimateEmitter):
    """
    JSON format for geospatial data (.json)
    """
    
    def render(self,request):
        pass
    
#Emitter.register('helloworld',HelloWorldEmitter,'text/html; charset=utf-8')
Emitter.register('html',HtmlEmitter,'text/html; charset=utf-8')
Emitter.register('shz',ShapefileEmitter,'application/zip; charset=utf-8')