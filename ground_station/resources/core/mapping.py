'''
Mapping.py: Objected Orientated Google Maps for Python
ReWritten by Chris Pham

Copyright OSURC, orginal code from GooMPy by Alec Singer and Simon D. Levy

This code is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as
published by the Free Software Foundation, either version 3 of the 
License, or (at your option) any later version.
This code is distributed in the hope that it will be useful,     
but WITHOUT ANY WARRANTY without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
You should have received a copy of the GNU Lesser General Public License 
along with this code.  If not, see <http://www.gnu.org/licenses/>.

'''

#####################################
# Imports
#####################################
# Python native imports
import math
import urllib2
from io import StringIO, BytesIO
import os
import time
import PIL.Image
import PIL.ImageDraw
import signing

#####################################
# Constants
#####################################
_KEYS = []
# Number of pixels in half the earth's circumference at zoom = 21
_EARTHPIX = 268435456
# Number of decimal places for rounding coordinates
_DEGREE_PRECISION = 4
# Larget tile we can grab without paying
_TILESIZE = 640
# Fastest rate at which we can download tiles without paying
_GRABRATE = 4
# Pixel Radius of Earth for calculations
_PIXRAD = _EARTHPIX / math.pi
_DISPLAYPIX = _EARTHPIX / 2000

file_pointer = open('key', 'r')
for i in file_pointer:
    _KEYS.append(i.rstrip())
file_pointer.close()

class GMapsStitcher(object):
    def __init__(self, width, height,
                 latitude, longitude, zoom,
                 maptype, radius_meters=None, num_tiles=4, debug=False):
        self.latitude = latitude
        self.longitude = longitude
        self.start_latitude = latitude
        self.start_longitude = longitude
        self.width = width
        self.height = height
        self.zoom = zoom
        self.maptype = maptype
        self.radius_meters = radius_meters
        self.num_tiles = num_tiles
        self.display_image = self._new_image(width, height)
        self.debug = debug

        # Get the big image here
        self._fetch()
        self.center_display(latitude, longitude)
    
    def __str__(self):
        string_builder = ""
        string_builder += "Center of the displayed map: %4f, %4f\n" % (self.center_x, self.center_y)
        string_builder += "Center of the big map: %4fx%4f\n" % (self.start_longitude, self.start_longitude)
        string_builder += "Current latitude is: %4f, %4f\n" % (self.longitude, self.latitude)
        string_builder += "The top-left of the box: %dx%d\n" % (self.left_x, self.upper_y)
        string_builder += "Number of tiles genreated: %dx%d\n" % (self.num_tiles, self.num_tiles)
        string_builder += "Map Type: %s\n" % (self.maptype)
        string_builder += "Zoom Level: %s\n" % (self.zoom)
        string_builder += "Dimensions of Big Image: %dx%d\n" % (self.big_image.size[0], self.big_image.size[1])
        string_builder += "Dimensions of Displayed Image: %dx%d\n" % (self.width, self.height)
        string_builder += "LatLong of Northwest Corner: %4f, %4f\n" % (self.northwest)
        string_builder += "LatLong of Southeast Corner: %4f, %4f\n" % (self.southeast)
        return string_builder

    def _new_image(self, width, height):
        return PIL.Image.new('RGBA', (width, height))

    def _fast_round(self, value, precision):
        return int(value * 10 ** precision) / 10. ** precision

    def _pixels_to_degrees(self, pixels, zoom):
        return pixels * 2 ** (21-zoom)

    def _pixels_to_meters(self):
          # https://groups.google.com/forum/#!topic/google-maps-js-api-v3/hDRO4oHVSeM
        return 2 ** self.zoom / (156543.03392 * math.cos(math.radians(self.latitude)))

    def _grab_tile(self, longitude, latitude, sleeptime=0):
        # Make the url string for polling
        # GET request header gets appended to the string
        urlbase = 'https://maps.googleapis.com/maps/api/staticmap?'
        urlbase += 'center=%.4f,%.4f&zoom=%d&maptype=%s&size=%dx%d&format=png&key=%s'

        # Fill the formatting
        specs = self._fast_round(latitude, 4), self._fast_round(longitude, 4), self.zoom, self.maptype, _TILESIZE, _TILESIZE, _KEYS[0]
        filename = 'Resources/Maps/' + ('%.4f_%.4f_%d_%s_%d_%d_%s' % specs) + '.png'

        # Tile Image object
        tile_object = None

        if os.path.isfile(filename):
            tile_object = PIL.Image.open(filename)

        # If file on filesystem
        else:
            # make the url
            url = urlbase % specs
            url = signing.sign_url(url, _KEYS[1])
            result = urllib2.urlopen(urllib2.Request(url)).read()
            tile_object = PIL.Image.open(BytesIO(result))
            if not os.path.exists('Resources/Maps'):
                os.mkdir('Resources/Maps')
            tile_object.save(filename)
            #Added to prevent timeouts on Google Servers
            time.sleep(sleeptime)

        return tile_object

    def _pixels_to_lon(self, iterator, lon_pixels):
        # Magic Lines, no idea
        degrees = self._pixels_to_degrees(((iterator) - self.num_tiles / 2) * _TILESIZE, self.zoom)
        return math.degrees((lon_pixels + degrees - _EARTHPIX) / _PIXRAD)

    def _pixels_to_lat(self, iterator, lat_pixels):
        # Magic Lines
        return math.degrees(math.pi / 2 - 2 * math.atan(
            math.exp(((lat_pixels + self._pixels_to_degrees((iterator - self.num_tiles / 2) * _TILESIZE, self.zoom)) - _EARTHPIX) / _PIXRAD)))

    def fetch_tiles(self):
        # cap floats to precision amount
        self.latitude = self._fast_round(self.latitude, _DEGREE_PRECISION)
        self.longitude = self._fast_round(self.longitude, _DEGREE_PRECISION)

        # number of tiles required to go from center latitude to desired radius in meters
        if self.radius_meters is not None:
            self.num_tiles = int(round(2*self._pixels_to_meters() / (_TILESIZE / 2. / self.radius_meters)))

        lon_pixels = _EARTHPIX + self.longitude * math.radians(_PIXRAD)

        sin_lat = math.sin(math.radians(self.latitude))
        lat_pixels = _EARTHPIX - _PIXRAD * math.log((1+sin_lat)/(1-sin_lat))/2
        self.big_size = self.num_tiles * _TILESIZE
        big_image = self._new_image(self.big_size, self.big_size)

        for j in range(self.num_tiles):
            lon = self._pixels_to_lon(j, lon_pixels)
            for k in range(self.num_tiles):
                lat = self._pixels_to_lat(k, lat_pixels)
                tile = self._grab_tile(lon, lat)
                big_image.paste(tile, (j * _TILESIZE, k * _TILESIZE))

        west = self._pixels_to_lon(0, lon_pixels)
        east = self._pixels_to_lon(self.num_tiles - 1, lon_pixels)

        north = self._pixels_to_lat(0, lat_pixels)
        south = self._pixels_to_lat(self.num_tiles - 1, lat_pixels)
        return big_image, (north, west), (south, east)

    def move_pix(self, dx, dy):
        self._constrain_x(dx)
        self._constrain_y(dy)
        self.update()

    def _constrain_x(self, diff):
        new_value = self.left_x - diff
        return new_value if (new_value > 0 and (new_value < self.big_image.size[0] - self.width)) else self.left_x

    def _constrain_y(self, diff):
        new_value = self.upper_y - diff
        return new_value if new_value > 0 and new_value < self.big_image.size[0] - self.height else self.upper_y

    def update(self):
        self.display_image.paste(self.big_image, (-self.left_x, -self.upper_y))
        # self.display_image.resize((self.image_zoom, self.image_zoom))

    def _fetch(self):
        self.big_image, self.northwest, self.southeast = self.fetch_tiles()

    def move_latlon(self, lat, lon):
        x, y = self._get_cartesian(lat, lon)

    def _get_cartesian(self, lat, lon):
        viewport_lat_nw, viewport_lon_nw = self.northwest
        viewport_lat_se, viewport_lon_se = self.southeast
        # print "Lat:", viewport_lat_nw, viewport_lat_se
        # print "Lon:", viewport_lon_nw, viewport_lon_se

        viewport_lat_diff = viewport_lat_nw - viewport_lat_se
        viewport_lon_diff = viewport_lon_se - viewport_lon_nw

        # print viewport_lon_diff, viewport_lat_diff

        bigimage_width = self.big_image.size[0]
        bigimage_height = self.big_image.size[1]

        pixel_per_lat = bigimage_height / viewport_lat_diff
        pixel_per_lon = bigimage_width / viewport_lon_diff
        # print "Pixel per:", pixel_per_lat, pixel_per_lon

        new_lat_gps_range_percentage = (viewport_lat_nw - lat)
        new_lon_gps_range_percentage = (lon - viewport_lon_nw)
        # print lon, viewport_lon_se

        # print "Percentages: ", new_lat_gps_range_percentage, new_lon_gps_range_percentage

        x = new_lon_gps_range_percentage * pixel_per_lon
        y = new_lat_gps_range_percentage * pixel_per_lat

        return int(x), int(y)

    def add_gps_location(self, lat, lon, shape, size, fill):
        x, y = self._get_cartesian(lat, lon)
        draw = PIL.ImageDraw.Draw(self.big_image)
        if shape is "ellipsis":
            draw.ellipsis((x-size, y-size, x+size, y+size), fill)
        else:
            draw.rectangle([x-size, y-size, x+size, y+size], fill)
        self.update()


    def center_display(self, lat, lon):
        x, y = self._get_cartesian(lat, lon)
        self.center_x = x
        self.center_y = y

        self.left_x = (self.center_x - (self.width/2))
        self.upper_y = (self.center_y - (self.height/2))
        self.update()


    def update_rover_map_location(self, lat, lon):
        print "I did nothing"

    def draw_circle(self, lat, lon, radius, fill):
        print "I did nothing"
