import unittest
import math
import random

import numpy as num

from pyrocko import orthodrome, util
from pyrocko import orthodrome_ext
import pyrocko.config

config = pyrocko.config.config()

r2d = 180./math.pi
d2r = 1./r2d
km = 1000.


class OrthodromeTestCase(unittest.TestCase):

    def get_critical_random_locations(self, ntest):
        '''
        Create list of ((lat1, lon1, lat2, lon2), assertions, exceptions)
        tuples.
        :param assertions: list of functions
        :param exceptions: list of expected exceptions

        TODO: expected exceptions may vary depending on the tested method.
        Maybe remove this or change logic.
        '''
        nasty_locations = [
            ((0., 0., 0., 0.), num.testing.assert_almost_equal, None),
            ((90., 0., -90., 0.), num.testing.assert_almost_equal, None),
            ((91., 0., -91., 0.), num.testing.assert_almost_equal, ValueError),
            ((0., -180., 0., 180.), num.testing.assert_almost_equal, None),
            ((1000., -1000., -1000., 1000.), num.testing.assert_almost_equal, ValueError)
        ]

        assert ntest >= len(nasty_locations)

        lats1 = num.random.uniform(-90., 90., ntest)
        lats2 = num.random.uniform(-90., 90., ntest)
        lons1 = num.random.uniform(-180., 180., ntest)
        lons2 = num.random.uniform(-180., 180., ntest)

        assertions = [num.testing.assert_almost_equal] * ntest
        exceptions = [None] * ntest

        for i, (llll, assertion, exception) in enumerate(nasty_locations):
            lats1[i], lons1[i], lats2[i], lons2[i] = llll
            assertions[i] = assertion
            exceptions[i] = exception

        return lats1, lons1, lats2, lons2, assertions #, exceptions

    def testAziBaziPythonC(self):
        from pyrocko.gf.meta import Location
        ntest = 100
        lats1, lons1, lats2, lons2, assertions = \
            self.get_critical_random_locations(ntest)

        for i in xrange(ntest):
            loc1 = Location(lat=lats1[i], lon=lons1[i])
            loc2 = Location(lat=lats2[i], lon=lons2[i])

            azibazi_py = loc1.azibazi_to(loc2)
            azibazi_c = orthodrome_ext.azibazi(
                loc1.lat, loc1.lon, loc2.lat, loc2.lon)

            assertion = assertions[i]
            #with self.assertRaises(exceptions[i]):
            assertion(azibazi_py, azibazi_c)

    def testDistancePythonC(self):
        ntest = 100
        lats1, lons1, lats2, lons2, assertions = self.get_critical_random_locations(ntest)
        for i in xrange(ntest):

            loc1 = orthodrome.Loc(lats1[i], lons1[i])
            loc2 = orthodrome.Loc(lats2[i], lons2[i])

            dist_py = orthodrome.distance_accurate50m(loc1, loc2)
            dist_c = orthodrome_ext.distance_accurate50m(
                loc1.lat, loc1.lon, loc2.lat, loc2.lon)

            assertions[i](dist_py, dist_c)

    def testGridDistances(self):
        for i in range(100):
            gsize = random.uniform(0., 1.)*2.*10.**random.uniform(4., 7.)
            north_grid, east_grid = num.meshgrid(
                num.linspace(-gsize/2., gsize/2., 11),
                num.linspace(-gsize/2., gsize/2., 11))

            north_grid = north_grid.flatten()
            east_grid = east_grid.flatten()

            lon = random.uniform(-180., 180.)
            lat = random.uniform(-90., 90.)

            lat_grid, lon_grid = orthodrome.ne_to_latlon(
                lat, lon, north_grid, east_grid)
            lat_grid_alt, lon_grid_alt = \
                orthodrome.ne_to_latlon_alternative_method(
                    lat, lon, north_grid, east_grid)

            for la, lo, no, ea in zip(
                    lat_grid, lon_grid, north_grid, east_grid):
                a = orthodrome.Loc(lat=la, lon=lo)
                b = orthodrome.Loc(lat=lat, lon=lon)

                cd = orthodrome.cosdelta(a, b)
                assert cd <= 1.0
                d = num.arccos(cd)*config.earthradius
                d2 = math.sqrt(no**2+ea**2)
                assert not (abs(d-d2) > 1.0e-3 and d2 > 1.)

    def OFF_test_local_distances(self):

        for reflat, reflon in [
                (0.0, 0.0),
                (10.0, 10.0),
                (90.0, 0.0),
                (-90.0, 0.0),
                (0.0, 180.0),
                (0.0, -180.0),
                (90.0, 180.0)]:

            north, east = serialgrid(num.linspace(-10*km, 10*km, 21),
                                     num.linspace(-10*km, 10*km, 21))

            lat, lon = orthodrome.ne_to_latlon2(reflat, reflon, north, east)
            north2, east2 = orthodrome.latlon_to_ne2(reflat, reflon, lat, lon)
            dist1 = num.sqrt(north**2 + east**2)
            dist2 = num.sqrt(north2**2 + east2**2)
            dist3 = orthodrome.distance_accurate15nm(reflat, reflon, lat, lon)
            assert num.all(num.abs(dist1-dist2) < 0.0001)
            assert num.all(num.abs(dist1-dist3) < 0.0001)

    def test_midpoint(self):
        center_lons = num.linspace(0., 180., 5)
        center_lats = [0., 89.]
        npoints = 10000.
        half_side_length = 1000000.
        distance_error_max = 50000.
        for lat in center_lats:
            for lon in center_lons:
                n = num.random.uniform(
                    -half_side_length, half_side_length, npoints)
                e = num.random.uniform(
                    -half_side_length, half_side_length, npoints)
                dlats, dlons = orthodrome.ne_to_latlon(lat, lon, n, e)
                clat, clon = orthodrome.geographic_midpoint(dlats, dlons)
                d = orthodrome.distance_accurate50m_numpy(
                    clat, clon, lat, lon)[0]
                if False:
                    import matplotlib.pyplot as plt
                    fig = plt.figure()
                    ax = fig.add_subplot(111)
                    ax.scatter(n, e)
                    c_n, c_e = orthodrome.latlon_to_ne_numpy(
                        lat, lon, clat, clon)
                    ax.plot(c_n, c_e, 'ro')
                    plt.show()
                self.assertTrue(d < distance_error_max, 'Distance %s > %s' %
                                (d, distance_error_max) +
                                '(maximum error)\n tested lat/lon: %s/%s' %
                                (lat, lon))


def serialgrid(x, y):
    return num.repeat(x, y.size), num.tile(y, x.size)


def plot_erroneous_ne_to_latlon():
    import gmtpy
    import random
    import subprocess
    import time

    while True:
        w, h = 20, 15

        gsize = random.uniform(0., 1.)*4.*10.**random.uniform(4., 7.)
        north_grid, east_grid = num.meshgrid(
            num.linspace(-gsize/2., gsize/2., 11),
            num.linspace(-gsize/2., gsize/2., 11))

        north_grid = north_grid.flatten()
        east_grid = east_grid.flatten()

        lat_delta = gsize/config.earthradius*r2d*2.
        lon = random.uniform(-180., 180.)
        lat = random.uniform(-90., 90.)

        print gsize/1000.

        lat_grid, lon_grid = orthodrome.ne_to_latlon(
            lat, lon, north_grid, east_grid)
        lat_grid_alt, lon_grid_alt = \
            orthodrome.ne_to_latlon_alternative_method(
                lat, lon, north_grid, east_grid)

        maxerrlat = num.max(num.abs(lat_grid-lat_grid_alt))
        maxerrlon = num.max(num.abs(lon_grid-lon_grid_alt))
        eps = 1.0e-8
        if maxerrlon > eps or maxerrlat > eps:
            print lat, lon, maxerrlat, maxerrlon

            gmt = gmtpy.GMT(
                config={
                    'PLOT_DEGREE_FORMAT': 'ddd.xxxF',
                    'PAPER_MEDIA': 'Custom_%ix%i' % (w*gmtpy.cm, h*gmtpy.cm),
                    'GRID_PEN_PRIMARY': 'thinnest/0/50/0'})

            south = max(-85., lat - 0.5*lat_delta)
            north = min(85., lat + 0.5*lat_delta)

            lon_delta = lat_delta/math.cos(lat*d2r)

            delta = lat_delta/360.*config.earthradius*2.*math.pi
            scale_km = gmtpy.nice_value(delta/10.)/1000.

            west = lon - 0.5*lon_delta
            east = lon + 0.5*lon_delta

            x, y = (west, east), (south, north)
            xax = gmtpy.Ax(mode='min-max', approx_ticks=4.)
            yax = gmtpy.Ax(mode='min-max', approx_ticks=4.)
            scaler = gmtpy.ScaleGuru(data_tuples=[(x, y)], axes=(xax, yax))
            scaler['R'] = '-Rg'
            layout = gmt.default_layout()
            mw = 2.5*gmtpy.cm
            layout.set_fixed_margins(
                mw, mw, mw/gmtpy.golden_ratio, mw/gmtpy.golden_ratio)
            widget = layout.get_widget()
            # widget['J'] =  ('-JT%g/%g'  % (lon, lat)) + '/%(width)gp'
            widget['J'] = (
                '-JE%g/%g/%g' % (lon, lat, min(lat_delta/2., 180.)))\
                + '/%(width)gp'
            aspect = gmtpy.aspect_for_projection(*(widget.J() + scaler.R()))
            widget.set_aspect(aspect)

            gmt.psbasemap(
                B='5g5',
                L=('x%gp/%gp/%g/%g/%gk' % (
                    widget.width()/2., widget.height()/7.,
                    lon, lat, scale_km)),
                *(widget.JXY()+scaler.R()))

            gmt.psxy(
                in_columns=(lon_grid, lat_grid),
                S='x10p', W='1p/200/0/0', *(widget.JXY()+scaler.R()))
            gmt.psxy(
                in_columns=(lon_grid_alt, lat_grid_alt),
                S='c10p', W='1p/0/0/200', *(widget.JXY()+scaler.R()))

            gmt.save('orthodrome.pdf')
            subprocess.call(['xpdf', '-remote', 'ortho', '-reload'])
            time.sleep(2)
        else:
            print 'ok', gsize, lat, lon

if __name__ == "__main__":
    util.setup_logging('test_orthodrome', 'warning')
    unittest.main()
