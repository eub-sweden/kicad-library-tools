# generators is free software: you can redistribute it and/or modify it under the terms
# of the GNU General Public License as published by the Free Software Foundation, either
# version 3 of the License, or (at your option) any later version.
#
# generators is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# generators. If not, see < http://www.gnu.org/licenses/ >.
#
# (C) The KiCad Librarian Team

"""Pad factories for the grid array (BGA) generator.

Different styles of defining the pads of a grid array are supported via
different PadFactory implementations.
"""

import logging
from collections.abc import Iterator
from typing import Any, NamedTuple

from KicadModTree import Pad
from kilibs.config import ipc_rules
from kilibs.geom import Vector2D

from generators.tools.footprint.ipc_pad_size_calculators import ipc_ball_get_pad_size
from generators.tools.pad_factory import PadFactory, PadInfo, DevicePadType

from .spec import GridArraySpec


class _GridLayoutPadStyle(NamedTuple):
    """The fully-resolved pad style of one layout.

    The part-level default style is resolved once in `BgaGridPadFactory`, and then
    each layout's overrides are merged over it to produce one `_LayoutPadStyle` per
    layout. This is used to produce the `PadInfo` of each pad in each layout.
    """

    size: Vector2D
    """The pad size in mm."""
    shape: str
    """The pad shape (one of the `Pad.SHAPE_*` strings)."""
    paste_shape: str | None
    """The solder-paste opening shape, or `None` to use `shape`."""
    paste_margin: float
    """The solder-paste margin in mm."""


class BgaGridPadFactory(PadFactory):
    """A pad factory that produces the pads of a grid-array (BGA) part.

    One part can have multiple "grid layouts" (e.g. of different ball pitches),
    and each grid layout usually has multiple pads.

    The pads are defined by the part's grid layouts in the `GridArraySpec`. This
    factory resolves the part-level default pad style and yields one `PadInfo`
    per pad, applying any per-layout overrides.
    """

    def __init__(self, spec: GridArraySpec) -> None:
        """Create the pad factory for the given grid array spec.

        Args:
            spec: The grid array specification.
        """
        self._spec = spec
        self._default_style = _GridLayoutPadStyle(
            size=self._resolve_default_pad_size(spec),
            shape=spec.spec.get("pad_shape", "circle"),
            paste_shape=spec.spec.get("paste_shape"),
            paste_margin=spec.spec.get("paste_margin", 0.0),
        )

    @property
    def default_pad_size(self) -> Vector2D:
        """The part's default pad size in mm."""
        return self._default_style.size

    def pads(self) -> Iterator[PadInfo]:
        """Yield the resolved `PadInfo` of every pad of the part."""
        for layout in self._spec.layout_data_list:

            style = self._style_for(layout.layout_dict)

            for pad_data in layout.pad_data_list:
                yield PadInfo(
                    name=pad_data.name,
                    position=pad_data.position,
                    size=style.size,
                    shape=style.shape,
                    fp_pad_type=Pad.TYPE_SMT,
                    device_pad_type=DevicePadType.SMD_BALL,
                    fab_property=Pad.FabProperty.BGA,
                    paste_shape=style.paste_shape,
                    paste_margin=style.paste_margin,
                )

    def _style_for(self, layout_dict: dict[str, Any]) -> _GridLayoutPadStyle:
        """Resolve the pad style of one layout by merging its overrides over the
        part-level default."""

        default = self._default_style

        return _GridLayoutPadStyle(
            size=Vector2D(layout_dict.get("pad_size") or default.size),
            shape=layout_dict.get("pad_shape", default.shape),
            paste_shape=layout_dict.get("paste_shape", default.paste_shape),
            paste_margin=layout_dict.get("paste_margin", default.paste_margin),
        )

    @staticmethod
    def _resolve_default_pad_size(spec: GridArraySpec) -> Vector2D:
        """Resolve the part-level default pad size from the spec.

        The size is either set explicitly via `pad_diameter`, or calculated per
        IPC rules from the ball type and diameter.

        Args:
            spec: The grid array specification.

        Returns:
            The default pad size in mm.
        """
        if "pad_diameter" in spec.spec:
            pad_diameter = spec.spec["pad_diameter"]
            logging.debug(
                f"Pad size of {spec.id} is set by the footprint definition. "
                "This should only be done for manufacturer-specific footprints."
            )
        elif "ball_type" in spec.spec and "ball_diameter" in spec.spec:
            # IPC calculation mode
            ball_diameter = float(spec.spec["ball_diameter"])
            ball_type = str(spec.spec["ball_type"])

            ball_type = spec._ball_type_from_str(ball_type)

            ball_rules = ipc_rules.DEFAULT_IPC_BALL_RULES

            pad_diameter = ipc_ball_get_pad_size(
                ball_rules=ball_rules,
                density=spec.ipc_density,
                ball_type=ball_type,
                ball_diameter=ball_diameter,
            )
        elif "ball_type" in spec.spec and "ball_diameter" not in spec.spec:
            raise KeyError(f"{spec.id}: Ball diameter is missing. Aborting.")
        elif "ball_diameter" in spec.spec and "ball_type" not in spec.spec:
            raise KeyError(f"{spec.id}: Ball type is missing. Aborting.")
        else:
            raise KeyError(
                f"{spec.id}: The config file must include 'ball_type' and "
                "'ball_diameter' or 'pad_diameter'. Aborting."
            )
        return Vector2D(pad_diameter, pad_diameter)


def make_pad_factory(spec: GridArraySpec) -> BgaGridPadFactory:
    """Create the pad factory matching the part's pad definition style.

    Today only the grid-based factory exists. When explicit pad tables are
    supported, this is the single place to select a table-driven factory for
    parts that carry a pad table.

    Args:
        spec: The grid array specification.

    Returns:
        A pad factory suitable for the spec.
    """
    return BgaGridPadFactory(spec)
