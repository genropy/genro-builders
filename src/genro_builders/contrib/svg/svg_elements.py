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
    def graphics(self, **kwargs):
        """SVG graphics content: any graphical element."""
        ...

    @abstract(sub_tags="*")
    def containerElement(self, **kwargs):
        """SVG container content: elements that can hold children."""
        ...

    # -------------------------------------------------------------------
    # Structural elements
    # -------------------------------------------------------------------

    @element(sub_tags="*")
    def svg(self, **kwargs):
        """Root SVG container or nested SVG viewport."""
        ...

    @element(sub_tags="*")
    def g(self, **kwargs):
        """Group container for applying transforms and styles."""
        ...

    @element(sub_tags="*")
    def defs(self, **kwargs):
        """Container for referenced elements (gradients, patterns, etc.)."""
        ...

    @element(sub_tags="*")
    def symbol(self, **kwargs):
        """Reusable graphical template, rendered only when referenced by <use>."""
        ...

    @element(sub_tags="")
    def use(self, **kwargs):
        """Reference and render a <symbol> or other element."""
        ...

    # -------------------------------------------------------------------
    # Shape elements (leaf — no children)
    # -------------------------------------------------------------------

    @element(sub_tags="")
    def rect(self, **kwargs):
        """Rectangle."""
        ...

    @element(sub_tags="")
    def circle(self, **kwargs):
        """Circle."""
        ...

    @element(sub_tags="")
    def ellipse(self, **kwargs):
        """Ellipse."""
        ...

    @element(sub_tags="")
    def line(self, **kwargs):
        """Line segment between two points."""
        ...

    @element(sub_tags="")
    def polyline(self, **kwargs):
        """Open shape of connected line segments."""
        ...

    @element(sub_tags="")
    def polygon(self, **kwargs):
        """Closed shape of connected line segments."""
        ...

    @element(sub_tags="")
    def path(self, **kwargs):
        """Arbitrary shape defined by path commands (d attribute)."""
        ...

    @element(sub_tags="")
    def image(self, **kwargs):
        """Embedded raster image."""
        ...

    # -------------------------------------------------------------------
    # Text elements
    # -------------------------------------------------------------------

    @element(sub_tags="tspan,textPath")
    def text(self, **kwargs):
        """Text block. Contains text content and optional <tspan>/<textPath>."""
        ...

    @element(sub_tags="")
    def tspan(self, **kwargs):
        """Inline text span within <text>."""
        ...

    @element(sub_tags="")
    def textPath(self, **kwargs):
        """Text rendered along a path shape."""
        ...

    # -------------------------------------------------------------------
    # Gradient and pattern elements
    # -------------------------------------------------------------------

    @element(sub_tags="stop")
    def linearGradient(self, **kwargs):
        """Linear gradient definition. Place inside <defs>."""
        ...

    @element(sub_tags="stop")
    def radialGradient(self, **kwargs):
        """Radial gradient definition. Place inside <defs>."""
        ...

    @element(sub_tags="")
    def stop(self, **kwargs):
        """Gradient stop (color and offset)."""
        ...

    @element(sub_tags="*")
    def pattern(self, **kwargs):
        """Tile pattern definition. Place inside <defs>."""
        ...

    # -------------------------------------------------------------------
    # Clipping and masking
    # -------------------------------------------------------------------

    @element(sub_tags="*")
    def clipPath(self, **kwargs):
        """Clipping path definition."""
        ...

    @element(sub_tags="*")
    def mask(self, **kwargs):
        """Alpha mask definition."""
        ...

    # -------------------------------------------------------------------
    # Marker
    # -------------------------------------------------------------------

    @element(sub_tags="*")
    def marker(self, **kwargs):
        """Marker symbol for line endpoints or vertices."""
        ...

    # -------------------------------------------------------------------
    # Filter elements
    # -------------------------------------------------------------------

    @element(sub_tags="*")
    def filter(self, **kwargs):
        """Filter effect container. Place inside <defs>."""
        ...

    @element(sub_tags="")
    def feGaussianBlur(self, **kwargs):
        """Gaussian blur filter primitive."""
        ...

    @element(sub_tags="")
    def feOffset(self, **kwargs):
        """Offset filter primitive."""
        ...

    @element(sub_tags="")
    def feBlend(self, **kwargs):
        """Blend filter primitive."""
        ...

    @element(sub_tags="")
    def feColorMatrix(self, **kwargs):
        """Color matrix filter primitive."""
        ...

    @element(sub_tags="")
    def feComposite(self, **kwargs):
        """Composite filter primitive."""
        ...

    @element(sub_tags="")
    def feFlood(self, **kwargs):
        """Flood fill filter primitive."""
        ...

    @element(sub_tags="*")
    def feMerge(self, **kwargs):
        """Merge filter primitive (container for feMergeNode)."""
        ...

    @element(sub_tags="")
    def feMergeNode(self, **kwargs):
        """Single input for feMerge."""
        ...

    @element(sub_tags="")
    def feDropShadow(self, **kwargs):
        """Drop shadow filter primitive (SVG 2)."""
        ...

    @element(sub_tags="*")
    def feDiffuseLighting(self, **kwargs):
        """Diffuse lighting filter primitive."""
        ...

    @element(sub_tags="*")
    def feSpecularLighting(self, **kwargs):
        """Specular lighting filter primitive."""
        ...

    @element(sub_tags="")
    def fePointLight(self, **kwargs):
        """Point light source for lighting filters."""
        ...

    @element(sub_tags="")
    def feDistantLight(self, **kwargs):
        """Distant light source for lighting filters."""
        ...

    @element(sub_tags="")
    def feSpotLight(self, **kwargs):
        """Spot light source for lighting filters."""
        ...

    @element(sub_tags="")
    def feMorphology(self, **kwargs):
        """Morphology filter primitive (erode/dilate)."""
        ...

    @element(sub_tags="")
    def feTurbulence(self, **kwargs):
        """Turbulence noise filter primitive."""
        ...

    @element(sub_tags="")
    def feDisplacementMap(self, **kwargs):
        """Displacement map filter primitive."""
        ...

    @element(sub_tags="")
    def feConvolveMatrix(self, **kwargs):
        """Convolution matrix filter primitive."""
        ...

    @element(sub_tags="")
    def feImage(self, **kwargs):
        """Image filter primitive."""
        ...

    @element(sub_tags="")
    def feTile(self, **kwargs):
        """Tile filter primitive."""
        ...

    # -------------------------------------------------------------------
    # Animation elements
    # -------------------------------------------------------------------

    @element(sub_tags="")
    def animate(self, **kwargs):
        """Animate an attribute over time."""
        ...

    @element(sub_tags="")
    def animateTransform(self, **kwargs):
        """Animate a transform attribute."""
        ...

    @element(sub_tags="")
    def animateMotion(self, **kwargs):
        """Animate motion along a path."""
        ...

    @element(sub_tags="")
    def set(self, **kwargs):
        """Set an attribute to a value for a duration."""
        ...

    # -------------------------------------------------------------------
    # Descriptive elements
    # -------------------------------------------------------------------

    @element(sub_tags="")
    def title(self, **kwargs):
        """Accessible title (tooltip in browsers)."""
        ...

    @element(sub_tags="")
    def desc(self, **kwargs):
        """Accessible description."""
        ...

    @element(sub_tags="")
    def metadata(self, **kwargs):
        """Metadata container (RDF, Dublin Core, etc.)."""
        ...

    # -------------------------------------------------------------------
    # Linking and foreign content
    # -------------------------------------------------------------------

    @element(sub_tags="*")
    def a(self, **kwargs):
        """Hyperlink wrapper."""
        ...

    @element(sub_tags="*")
    def foreignObject(self, **kwargs):
        """Container for non-SVG content (HTML, MathML)."""
        ...

    @element(sub_tags="*")
    def switch(self, **kwargs):
        """Conditional processing (renders first matching child)."""
        ...
