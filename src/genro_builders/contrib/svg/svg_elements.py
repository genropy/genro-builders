# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""SVG element definitions based on the W3C SVG 1.1 / SVG 2 specification.

Covers the most commonly used SVG elements organized by category:
structural, shape, text, gradient/pattern, filter, animation, and
descriptive. Elements are classified as container (sub_tags="*") or
leaf (sub_tags="") based on whether they accept child elements.

Attribute naming: SVG uses kebab-case (stroke-width) but Python
requires identifiers, so use underscore (stroke_width). The renderer
converts underscores to hyphens for presentation attributes.
"""

from __future__ import annotations

from genro_builders.builder import abstract, element


class SvgElements:
    """Mixin defining SVG elements for SvgBuilder."""

    # -------------------------------------------------------------------
    # Abstract content models
    # -------------------------------------------------------------------

    @abstract(sub_tags="*")
    def graphics(self):
        """SVG graphics content: any graphical element."""
        ...

    @abstract(sub_tags="*")
    def container_element(self):
        """SVG container content: elements that can hold children."""
        ...

    # -------------------------------------------------------------------
    # Structural elements
    # -------------------------------------------------------------------

    @element(sub_tags="*")
    def svg(self):
        """Root SVG container or nested SVG viewport."""
        ...

    @element(sub_tags="*")
    def g(self):
        """Group container for applying transforms and styles."""
        ...

    @element(sub_tags="*")
    def defs(self):
        """Container for referenced elements (gradients, patterns, etc.)."""
        ...

    @element(sub_tags="*")
    def symbol(self):
        """Reusable graphical template, rendered only when referenced by <use>."""
        ...

    @element(sub_tags="")
    def use(self):
        """Reference and render a <symbol> or other element."""
        ...

    # -------------------------------------------------------------------
    # Shape elements (leaf — no children)
    # -------------------------------------------------------------------

    @element(sub_tags="")
    def rect(self):
        """Rectangle."""
        ...

    @element(sub_tags="")
    def circle(self):
        """Circle."""
        ...

    @element(sub_tags="")
    def ellipse(self):
        """Ellipse."""
        ...

    @element(sub_tags="")
    def line(self):
        """Line segment between two points."""
        ...

    @element(sub_tags="")
    def polyline(self):
        """Open shape of connected line segments."""
        ...

    @element(sub_tags="")
    def polygon(self):
        """Closed shape of connected line segments."""
        ...

    @element(sub_tags="")
    def path(self):
        """Arbitrary shape defined by path commands (d attribute)."""
        ...

    @element(sub_tags="")
    def image(self):
        """Embedded raster image."""
        ...

    # -------------------------------------------------------------------
    # Text elements
    # -------------------------------------------------------------------

    @element(sub_tags="tspan,textPath")
    def text(self):
        """Text block. Contains text content and optional <tspan>/<textPath>."""
        ...

    @element(sub_tags="")
    def tspan(self):
        """Inline text span within <text>."""
        ...

    @element(sub_tags="")
    def textPath(self):
        """Text rendered along a path shape."""
        ...

    # -------------------------------------------------------------------
    # Gradient and pattern elements
    # -------------------------------------------------------------------

    @element(sub_tags="stop")
    def linearGradient(self):
        """Linear gradient definition. Place inside <defs>."""
        ...

    @element(sub_tags="stop")
    def radialGradient(self):
        """Radial gradient definition. Place inside <defs>."""
        ...

    @element(sub_tags="")
    def stop(self):
        """Gradient stop (color and offset)."""
        ...

    @element(sub_tags="*")
    def pattern(self):
        """Tile pattern definition. Place inside <defs>."""
        ...

    # -------------------------------------------------------------------
    # Clipping and masking
    # -------------------------------------------------------------------

    @element(sub_tags="*")
    def clipPath(self):
        """Clipping path definition."""
        ...

    @element(sub_tags="*")
    def mask(self):
        """Alpha mask definition."""
        ...

    # -------------------------------------------------------------------
    # Marker
    # -------------------------------------------------------------------

    @element(sub_tags="*")
    def marker(self):
        """Marker symbol for line endpoints or vertices."""
        ...

    # -------------------------------------------------------------------
    # Filter elements
    # -------------------------------------------------------------------

    @element(sub_tags="*")
    def filter(self):
        """Filter effect container. Place inside <defs>."""
        ...

    @element(sub_tags="")
    def feGaussianBlur(self):
        """Gaussian blur filter primitive."""
        ...

    @element(sub_tags="")
    def feOffset(self):
        """Offset filter primitive."""
        ...

    @element(sub_tags="")
    def feBlend(self):
        """Blend filter primitive."""
        ...

    @element(sub_tags="")
    def feColorMatrix(self):
        """Color matrix filter primitive."""
        ...

    @element(sub_tags="")
    def feComposite(self):
        """Composite filter primitive."""
        ...

    @element(sub_tags="")
    def feFlood(self):
        """Flood fill filter primitive."""
        ...

    @element(sub_tags="*")
    def feMerge(self):
        """Merge filter primitive (container for feMergeNode)."""
        ...

    @element(sub_tags="")
    def feMergeNode(self):
        """Single input for feMerge."""
        ...

    @element(sub_tags="")
    def feDropShadow(self):
        """Drop shadow filter primitive (SVG 2)."""
        ...

    @element(sub_tags="*")
    def feDiffuseLighting(self):
        """Diffuse lighting filter primitive."""
        ...

    @element(sub_tags="*")
    def feSpecularLighting(self):
        """Specular lighting filter primitive."""
        ...

    @element(sub_tags="")
    def fePointLight(self):
        """Point light source for lighting filters."""
        ...

    @element(sub_tags="")
    def feDistantLight(self):
        """Distant light source for lighting filters."""
        ...

    @element(sub_tags="")
    def feSpotLight(self):
        """Spot light source for lighting filters."""
        ...

    @element(sub_tags="")
    def feMorphology(self):
        """Morphology filter primitive (erode/dilate)."""
        ...

    @element(sub_tags="")
    def feTurbulence(self):
        """Turbulence noise filter primitive."""
        ...

    @element(sub_tags="")
    def feDisplacementMap(self):
        """Displacement map filter primitive."""
        ...

    @element(sub_tags="")
    def feConvolveMatrix(self):
        """Convolution matrix filter primitive."""
        ...

    @element(sub_tags="")
    def feImage(self):
        """Image filter primitive."""
        ...

    @element(sub_tags="")
    def feTile(self):
        """Tile filter primitive."""
        ...

    # -------------------------------------------------------------------
    # Animation elements
    # -------------------------------------------------------------------

    @element(sub_tags="")
    def animate(self):
        """Animate an attribute over time."""
        ...

    @element(sub_tags="")
    def animateTransform(self):
        """Animate a transform attribute."""
        ...

    @element(sub_tags="")
    def animateMotion(self):
        """Animate motion along a path."""
        ...

    @element(sub_tags="")
    def set(self):
        """Set an attribute to a value for a duration."""
        ...

    # -------------------------------------------------------------------
    # Descriptive elements
    # -------------------------------------------------------------------

    @element(sub_tags="")
    def title(self):
        """Accessible title (tooltip in browsers)."""
        ...

    @element(sub_tags="")
    def desc(self):
        """Accessible description."""
        ...

    @element(sub_tags="")
    def metadata(self):
        """Metadata container (RDF, Dublin Core, etc.)."""
        ...

    # -------------------------------------------------------------------
    # Linking and foreign content
    # -------------------------------------------------------------------

    @element(sub_tags="*")
    def a(self):
        """Hyperlink wrapper."""
        ...

    @element(sub_tags="*")
    def foreignObject(self):
        """Container for non-SVG content (HTML, MathML)."""
        ...

    @element(sub_tags="*")
    def switch(self):
        """Conditional processing (renders first matching child)."""
        ...
