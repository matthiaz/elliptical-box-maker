#!/usr/bin/env python

# We will use the inkex module with the predefined Effect base class.
import inkex
# The simplestyle module provides functions for style parsing.
#from simplestyle import *
import simplestyle
from math import *
from collections import namedtuple
import traceback

objStyle = simplestyle.formatStyle(
    {'stroke': '#000000',
    'stroke-width': '0.1',
    'fill': 'none'
    })

def draw_SVG_square((w,h), (x,y), parent):
    attribs = {
        'style': objStyle,
        'height': str(h),
        'width': str(w),
        'x': str(x),
        'y': str(y)
    }
    inkex.etree.SubElement(parent, inkex.addNS('rect', 'svg'), attribs)

def draw_SVG_ellipse((rx, ry), center, parent, start_end=(0, 2*pi), transform=''):
    ell_attribs = {'style': objStyle,
        inkex.addNS('cx', 'sodipodi'): str(center.x),
        inkex.addNS('cy', 'sodipodi'): str(center.y),
        inkex.addNS('rx', 'sodipodi'): str(rx),
        inkex.addNS('ry', 'sodipodi'): str(ry),
        inkex.addNS('start', 'sodipodi'): str(start_end[0]),
        inkex.addNS('end', 'sodipodi'): str(start_end[1]),
        inkex.addNS('open', 'sodipodi'): 'true',  #all ellipse sectors we will draw are open
        inkex.addNS('type', 'sodipodi'): 'arc',
        'transform': transform
    }
    inkex.etree.SubElement(parent, inkex.addNS('path', 'svg'), ell_attribs)


def draw_SVG_arc((rx, ry), x_axis_rot):
    arc_attribs = {'style': objStyle,
        'rx': str(rx),
        'ry': str(ry),
        'x-axis-rotation': str(x_axis_rot),
        'large-arc': '',
        'sweep': '',
        'x': '',
        'y': ''
        }
        #name='part'
    style = {'stroke': '#000000', 'fill': 'none'}
    drw = {'style':simplestyle.formatStyle(style),inkex.addNS('label','inkscape'):name,'d':XYstring}
    inkex.etree.SubElement(parent, inkex.addNS('path', 'svg'), drw)
    inkex.addNS('', 'svg')

def draw_SVG_text((cx, cy), txt, parent):
    text = inkex.etree.Element(inkex.addNS('text', 'svg'))
    text.text = txt
    text.set('x', str(cx))
    text.set('y', str(cy))
    style = {'text-align': 'center', 'text-anchor': 'middle'}
    text.set('style', formatStyle(style))
    parent.append(text)


def SVG_move_to(x, y):
    return "M %d %d" % (x, y)


def SVG_line_to(x, y):
    return "L %d %d" % (x, y)


def SVG_arc_to(rx, ry, x, y):
    la = sw = 0
    return "A %d %d 0 %d %d" % (rx, ry, la, sw, x, y)


def SVG_path(components):
    return '<path d="' + ' '.join(components) + '">'

def SVG_curve(parent, segments, style, closed=True):
    #pathStr = 'M '+ segments[0]
    pathStr = ' '.join(segments)
    if closed:
        pathStr += ' z'
    attributes = {
      'style': style,
      'd': pathStr}
    inkex.etree.SubElement(parent, inkex.addNS('path', 'svg'), attributes)

#draw an SVG line segment between the given (raw) points
def draw_SVG_line(start, end, parent):
    line_attribs = {'style': objStyle,
                    'd': 'M '+str(start.x)+','+str(start.y)+' L '+str(end.x)+','+str(end.y)}

    inkex.etree.SubElement(parent, inkex.addNS('path', 'svg'), line_attribs)


def _makeCurvedSurface(topLeft, (w, h), cutSpacing, hCutCount, thickness, parent):
    group = inkex.etree.SubElement(parent, 'g')
    width = Coordinate(w, 0)
    heigth = Coordinate(0, h)
    wCutCount = int(floor(w / cutSpacing))
    if wCutCount % 2 == 0:
        wCutCount += 1    # make sure we have an odd number of cuts
    xCutDist = w / wCutCount
    xSpacing = Coordinate(xCutDist, 0)
    ySpacing = Coordinate(0, cutSpacing)
    cutLength = h / hCutCount - cutSpacing
    cut = Coordinate(0, cutLength)
    notchEdges = [0]

    for cutIndex in range(wCutCount):
        if cutIndex % 2 == 1:  # make a notch here
            inset = Coordinate(0, thickness)
        else:
            inset = Coordinate(0, 0)

        aColStart = topLeft + xSpacing * cutIndex
        notchEdges.append(aColStart.x)

        if cutIndex > 0: # no cuts at x == 0
            draw_SVG_line(aColStart, aColStart + cut / 2, group)
            for j in range(hCutCount - 1):
                pos = aColStart + cut / 2 + ySpacing + (cut + ySpacing) * j
                draw_SVG_line(pos, pos + cut, group)
            draw_SVG_line(aColStart + heigth - cut / 2, aColStart + heigth, group)

        # these cuts run in the opposite direction
        bColStart = topLeft + xSpacing * cutIndex + xSpacing / 2
        for j in reversed(range(hCutCount)):
            end = bColStart + ySpacing / 2 + (cut + ySpacing) * j
            start = end + cut
            if j == 0:  # first row
                end += inset
            elif j == hCutCount - 1:  # last row
                start -= inset
            draw_SVG_line(start, end, group)

        #horizontal cuts (should be done last)
        draw_SVG_line(aColStart + inset, aColStart + inset + xSpacing, group)
        draw_SVG_line(aColStart + heigth - inset, aColStart + heigth - inset + xSpacing, group)

    draw_SVG_line(topLeft, topLeft + heigth, group)
    draw_SVG_line(topLeft + width, topLeft + width + heigth, group)
    notchEdges.append(w)
    return notchEdges

class Ellipse():
    nrPoints = 1000 #used for piecewise linear circumference calculation (ellipse circumference is tricky to calculate)
    # approximate circumfere: c = pi * (3 * (a + b) - sqrt(10 * a * b + 3 * (a ** 2 + b ** 2)))

    def __init__(self, w, h):
        self.h = h
        self.w = w
        EllipsePoint = namedtuple('EllipsePoint', 'angle coord cDist')
        self.ellData = [EllipsePoint(0, Coordinate(w/2, 0), 0)] # (angle, x, y, cumulative distance from angle = 0)
        angle = 0
        self.angleStep = 2 * pi / self.nrPoints
        #note: the render angle (ra) corresponds to the angle from the ellipse center (ca) according to:
        # ca = atan(w/h * tan(ra))
        for i in range(self.nrPoints):
            angle += self.angleStep
            prev = self.ellData[-1]
            x, y = w / 2 * cos(angle), h / 2 * sin(angle)
            self.ellData.append(EllipsePoint(angle, Coordinate(x, y), prev.cDist + hypot(prev.coord.x - x, prev.coord.y - y)))
        self.circumference = self.ellData[-1].cDist
        inkex.debug("circ: %d" % self.circumference)

    def rAngle(self, a):
        """Convert an angle measured from ellipse center to the angle used to generate ellData (used for lookups)"""
        cf = 0
        if a > pi / 2:
            cf = pi
        if a > 3 * pi / 2:
            cf = 2 * pi
        return atan(self.w / self.h * tan(a)) + cf

    def coordinateFromAngle(self, angle):
        """Coordinate of the point at angle."""
        return Coordinate(self.w / 2 * cos(angle), self.h / 2 * sin(angle))

    def notchData(self, angle, notchHeight):
        """Coordinate and angle for a notch at the given angle. The notch is perpendicular to the ellipse."""
        angle %= (2 * pi)
        #some special cases to avoid divide by zero:
        if angle == 0:
            return (0, Coordinate(self.w / 2 + notchHeight, 0))
        elif angle == pi:
            return (pi, Coordinate(-self.w / 2 - notchHeight, 0))
        elif angle == pi / 2:
            return(pi / 2, Coordinate(0, self.h / 2 + notchHeight))
        elif angle == 3 * pi / 2:
            return(3 * pi / 2, Coordinate(0, -self.h / 2 - notchHeight))

        x = self.w / 2 * cos(angle)
        derivative = self.h / self.w * -x / sqrt((self.w / 2) ** 2 - x ** 2)
        if angle > pi:
            derivative = -derivative

        normal = -1 / derivative
        nAngle = atan(normal)
        if angle > pi / 2 and angle < 3 * pi / 2:
            nAngle += pi

        nCoordinate = self.coordinateFromAngle(angle) + Coordinate(cos(nAngle), sin(nAngle)) * notchHeight
        return nCoordinate


    def distFromAngles(self, a1, a2):
        """Distance accross the surface from point at angle a2 to point at angle a2. Measured in CCW sense."""
        i1 = int(self.rAngle(a1) / self.angleStep)
        p1 = self.rAngle(a1) % self.angleStep
        l1 = self.ellData[i1 + 1].cDist - self.ellData[i1].cDist
        i2 = int(self.rAngle(a2) / self.angleStep)
        p2 = self.rAngle(a2) % self.angleStep
        l2 = self.ellData[i2 + 1].cDist - self.ellData[i2].cDist
        if a1 <= a2:
            len = self.ellData[i2].cDist - self.ellData[i1].cDist + l2 * p2 - l1 * p1
        else:
            len = self.circumference + self.ellData[i2].cDist - self.ellData[i1].cDist
        return len

    def angleFromDist(self, startAngle, relDist):
        """Returns the angle that you get when starting at startAngle and moving a distance (dist) in CCW direction"""
        si = int(self.rAngle(startAngle) / self.angleStep)
        p = self.rAngle(startAngle) % self.angleStep

        l = self.ellData[si + 1].cDist - self.ellData[si].cDist

        startDist = self.ellData[si].cDist + p * l

        absDist = relDist + startDist

        if absDist > self.ellData[-1].cDist:  # wrap around zero angle
            absDist -= self.ellData[-1].cDist

        iMin = 0
        iMax = self.nrPoints
        count = 0
        while iMax - iMin > 1:  # binary search
            count += 1
            iHalf = iMin + (iMax - iMin) // 2
            if self.ellData[iHalf].cDist < absDist:
                iMin = iHalf
            else:
                iMax = iHalf

        stepDist = self.ellData[iMax].cDist - self.ellData[iMin].cDist
        return self.ellData[iMin].angle + self.angleStep * (absDist - self.ellData[iMin].cDist)/stepDist


class Coordinate:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __add__(self, other):
        return Coordinate(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        return Coordinate(self.x - other.x, self.y - other.y)

    def __mul__(self, factor):
        return Coordinate(self.x * factor, self.y * factor)

    def __div__(self, quotient):
        return Coordinate(self.x / quotient, self.y / quotient)


class EllipticalBox(inkex.Effect):
    """
    Creates a new layer with the drawings for a parametrically generaded box.
    """
    def __init__(self):
        inkex.Effect.__init__(self)

        self.OptionParser.add_option('-t', '--thickness', action = 'store',
          type = 'float', dest = 'thickness', default = '3.0',
          help = 'Material thickness')

        self.OptionParser.add_option('-x', '--width', action = 'store',
          type = 'float', dest = 'width', default = '3.0',
          help = 'Box width')

        self.OptionParser.add_option('-z', '--heigth', action = 'store',
          type = 'float', dest = 'heigth', default = '10.0',
          help = 'Box heigth')

        self.OptionParser.add_option('-y', '--depth', action = 'store',
          type = 'float', dest = 'depth', default = '3.0',
          help = 'Box depth')

        self.OptionParser.add_option('-d', '--cut_dist', action = 'store',
          type = 'float', dest = 'cut_dist', default = '1.5',
          help = 'Distance between cuts on the wrap around. Note that this value will change slightly to evenly fill up the available space.')

        self.OptionParser.add_option('-c', '--cut_nr', action = 'store',
          type = 'int', dest = 'cut_nr', default = '3',
          help = 'Number of cuts across the depth of the box.')

        self.OptionParser.add_option('-a', '--lid_angle', action = 'store',
          type = 'float', dest = 'lid_angle', default = '120',
          help = 'Angle that forms the lid (in degrees, measured from centerpoint of the ellipse)')

        self.OptionParser.add_option('-b', '--body_ribcount', action = 'store',
          type = 'int', dest = 'body_ribcount', default = '0',
          help = 'Number of ribs in the body')

        self.OptionParser.add_option('-l', '--lid_ribcount', action = 'store',
          type = 'int', dest = 'lid_ribcount', default = '0',
          help = 'Number of ribs in the lid')


    def effect(self):
        """
        Draws as basic elliptical box, based on provided parameters
        """

        # convert units
        unit = 'mm'
        H = inkex.unittouu(str(self.options.heigth) + unit)
        W = inkex.unittouu(str(self.options.width) + unit)
        D = inkex.unittouu(str(self.options.depth) + unit)
        thickness = inkex.unittouu(str(self.options.thickness) + unit)
        cutSpacing = inkex.unittouu(str(self.options.cut_dist) + unit)
        cutNr = self.options.cut_nr

        # input sanity check
        error = False
        if min(H, W, D) == 0:
            inkex.errormsg(_('Error: Dimensions must be non zero'))
            error = True

        if cutNr < 1:
            inkex.errormsg(_('Error: Number of cuts should be at least 1'))
            error = True
        if error:
            exit()

        svg = self.document.getroot()
        docWidth = inkex.unittouu(svg.get('width'))
        docHeigth = inkex.unittouu(svg.attrib['height'])

        layer = inkex.etree.SubElement(svg, 'g')
        layer.set(inkex.addNS('label', 'inkscape'), 'Elliptical Box')
        layer.set(inkex.addNS('groupmode', 'inkscape'), 'layer')

        # elliptical sides
        elCenter = Coordinate(docWidth / 2, 2 * D + H / 2)

        ell = Ellipse(W, H)

        #body and lid
        lidAngleRad = self.options.lid_angle * 2 * pi / 360
        lidStartAngle = pi / 2 - lidAngleRad / 2
        lidEndAngle = pi / 2 + lidAngleRad / 2

        lidLength = ell.distFromAngles(lidStartAngle, lidEndAngle)
        bodyLength = ell.distFromAngles(lidEndAngle, lidStartAngle)
        inkex.debug('lid start: %f, end: %f, calc. end:%f'% (lidStartAngle*360/2/pi, lidEndAngle*360/2/pi, ell.angleFromDist(lidStartAngle, lidLength)*360/2/pi))

        bodyNotches = _makeCurvedSurface(Coordinate(0, 0), (bodyLength, D), cutSpacing, cutNr, thickness, layer)
        lidNotches = _makeCurvedSurface(Coordinate(0, D+1), (lidLength, D), cutSpacing, cutNr, thickness, layer)
        a1 = lidEndAngle

        # create elliptical sides
        # body
        group = inkex.etree.SubElement(layer, 'g')
        for n in range(1, len(bodyNotches) - 1):
            startA = ell.angleFromDist(lidEndAngle, bodyNotches[n])
            endA = ell.angleFromDist(lidEndAngle, bodyNotches[n + 1])
            c1 = elCenter + ell.coordinateFromAngle(endA)
            c2 = ell.notchData(endA, thickness)
            a2 = atan2((W/2 + thickness) * c2.y, (H/2 + thickness) * c2.x)

            c2 += elCenter
            if n % 2 == 1:
                draw_SVG_ellipse((W / 2, H / 2), elCenter, group, (startA, endA))
                draw_SVG_line(c1, c2, group)
            else:
                draw_SVG_ellipse((W / 2 + thickness, H / 2 + thickness), elCenter, group, (a1, a2))
                draw_SVG_line(c2, c1, group)

            a1 = a2
        # lid
        for n in range(1, len(lidNotches) - 1):
            startA = ell.angleFromDist(lidStartAngle, lidNotches[n])
            endA = ell.angleFromDist(lidStartAngle, lidNotches[n + 1])
            c1 = elCenter + ell.coordinateFromAngle(endA)
            c2 = ell.notchData(endA, thickness)
            a2 = atan2((W/2 + thickness) * c2.y, (H/2 + thickness) * c2.x)

            c2 += elCenter
            if n % 2 == 1:
                draw_SVG_ellipse((W / 2, H / 2), elCenter, group, (startA, endA))
                draw_SVG_line(c1, c2, group)
            else:
                draw_SVG_ellipse((W / 2 + thickness, H / 2 + thickness), elCenter, group, (a1, a2))
                draw_SVG_line(c2, c1, group)

            a1 = a2

# Create effect instance and apply it.
effect = EllipticalBox()
effect.affect()
