from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Dict, List, Union

from securicad.model.exceptions import (
    DuplicateViewObjectException,  # type: ignore pylint: disable=import-error; type: ignore pylint: disable=import-error
)

from android_parser.utilities.log import log

if TYPE_CHECKING:
    from securicad.model.object import Object
    from securicad.model.visual.container import Container
    from securicad.model.visual.group import Group
    from securicad.model.visual.view import View

    from android_parser.components.application import AndroidComponent, Application
    from android_parser.main import AndroidParser

READ_FILE = None
SAVE_PATH = None

colors = ["#4287f5", "#b042f5", "#f54298", "#f52298", "#6fe240", "#6fd640", "#e6ac40"]
group_limit = 20  # Amount of groups that areallowed in a view for them to be defaulted to expand=True
default_icon = "App"


class Direction(Enum):
    LEFT = 0
    RIGHT = 1
    UP = 2
    DOWN = 3


class BoundingBox:
    def __init__(
        self, x_min: int = -100, x_max: int = 100, y_min: int = -100, y_max: int = 100
    ):
        # One item will have coordinates 0,0 : but will require 100 on each side for correct padding
        self.x_min: int = x_min
        self.x_max: int = x_max
        self.y_min: int = y_min
        self.y_max: int = y_max
        # Coordinates
        self.ul = (self.x_min, self.y_max)
        self.bl = (self.x_min, self.y_min)
        self.ur = (self.x_max, self.y_max)
        self.br = (self.x_max, self.y_min)

    def coordinates(self):
        self.ul = (self.x_min, self.y_max)
        self.bl = (self.x_min, self.y_min)
        self.ur = (self.x_max, self.y_max)
        self.br = (self.x_max, self.y_min)
        print(f"({self.ul}, {self.ur})\n({self.bl}, {self.br})")

    def correct_overlap(self, target: BoundingBox, direction: Direction, padding: int):
        """Will place this BoundingBox on the correct side of the target\n
        Keyword Arguments:\n
        \t target - The BoundingBox to fit against
        \t direction - The direction one wish to place boundingbox against
        \t padding - The incremental value to shift this BoundingBox with if it's not correctly placed
        """
        if direction == Direction.LEFT:
            while not (self.x_max <= target.x_min):
                self.x_min -= padding
                self.x_max -= padding
        elif direction == Direction.RIGHT:
            while not (self.x_min >= target.x_max):
                self.x_min += padding
                self.x_max += padding
        elif direction == Direction.UP:
            while not (self.y_min < target.y_max):
                self.y_min += padding
                self.y_max += padding
        elif direction == Direction.DOWN:
            while not (self.y_max > target.y_min):
                self.y_min -= padding
                self.y_max -= padding

    def adjust_parent_bounding_box(self, candidate: BoundingBox):
        """Evaluates if the coordinates of the candidate BoundingBox exceeds
        the coordinates in the target. We need this for later so that we can place the groups
        in the view without them overlapping
        """
        self.x_min = self.x_min if candidate.x_min > self.x_min else candidate.x_min
        self.x_max = self.x_max if candidate.x_max < self.x_max else candidate.x_max
        self.y_min = self.y_min if candidate.y_min > self.y_min else candidate.y_min
        self.y_max = self.y_max if candidate.y_max < self.y_max else candidate.y_max

    def pad(self, padding: int = 150):
        self.x_min -= padding  # Padding for next group
        self.x_max += padding
        self.y_min -= padding
        self.y_max -= padding

    def get_width(self) -> int:
        return self.x_max - self.x_min

    def get_height(self) -> int:
        return self.y_max - self.y_min


groups: Dict[str, Union[Group, Container]] = {}


def generate_views(parser: AndroidParser):
    application_view(parser)


def add_objects_horizontally(
    group: Group,
    items: List[Object],
    padding: int,
    y: int = 0,
    model_view: bool = False,
) -> BoundingBox:
    f"""Helper function to add items horizontally in a group
    Keyword arguments:\n
    \t group - A ModelView Group Object \n
    \t items - A List of Objects \n
    \t padding - The distance between two objects\n
    \t y - Where in the vertical line the objects should be placed \n
    \t model_view - if group is of type "ModelView" or Groups are added to other groups
    Returns: \n
        The bounding box tuple in x-axle BoundingBox(x_min, x_max, 0, 0)
    """
    x: float | int = 0
    x_min: float | int = 0
    x_max: float | int = 0
    offset = (padding * 0.5) if len(items) % 2 == 0 else 0
    if len(items) == 1:
        if model_view:
            items[0].x = 0  # type: ignore
            items[0].y = int(y)  # type: ignore
        else:
            try:
                group.add_object(items[0], 0, int(y))
            except DuplicateViewObjectException as e:
                log.error(f"{e}")
        return BoundingBox(0, 0, 0, 0)
    elif len(items) % 2 == 0:
        total_x = padding * len(items)
        for i in range(0, len(items)):
            item = items[i]
            x = (offset + (total_x / -2)) + padding * ((i + 1) - 1)
            if model_view:
                item.x = int(x)  # type: ignore
                item.y = int(y)  # type: ignore
            else:
                try:
                    group.add_object(item, int(x), int(y))
                except DuplicateViewObjectException as e:
                    log.error(f"{e}")
            x_min = x_min if x > x_min else x
            x_max = x_max if x < x_max else x
    else:
        for i, item in enumerate(items):
            x += (pow(-1, i) * padding) * i
            if model_view:
                item.x = int(x)  # type: ignore
                item.y = int(y)  # type: ignore
            else:
                try:
                    group.add_object(item, int(x), int(y))
                except DuplicateViewObjectException as e:
                    log.error(f"{e}")
            x_min = x_min if x > x_min else x
            x_max = x_max if x < x_max else x
    return BoundingBox(int(x_min), int(x_max), 0, 0)


def place_service_boxes_in_view(
    bounding_boxes: Dict[Union[Group, Container], BoundingBox],
    view: View,
    padding: int = 150,
) -> None:
    f"""Will place the large boundingboxes representing a service in the view \n
    Keyword arguments: \n
    \t bounding_boxes - A dict containing the groups and its corresponding coordinates (BoundingBox)
    \t view - The view element to place the groups in
    \t pad - an integer override for the padding between groups
    """
    groups_added: list[Group | Container] = list()
    simple_view = True if len(bounding_boxes.values()) >= group_limit else False
    group: Group | Container
    bb: BoundingBox
    for i, (group, bb) in enumerate(bounding_boxes.items()):
        if simple_view:
            row = (int)(i / 10)
            x = 200 * (i % 10)
            y = row * 200
        else:
            bb.pad(padding=padding)
            if i % 2 == 0:
                direction = Direction.LEFT
            else:
                direction = Direction.RIGHT
            for target in groups_added:
                target_bb = bounding_boxes.get(target)
                if target_bb:
                    bb.correct_overlap(target_bb, direction, padding=5)
            x = (bb.x_max + bb.x_min) / 2
            y = 0
        group.x = int(x)  # type: ignore
        group.y = int(y)  # type: ignore
        groups_added.append(group)


def component_view(parser: AndroidParser, component: AndroidComponent) -> None:
    # bounding_boxes: Dict[Group, BoundingBox] = {}
    padding = 200
    view_name: str = component.name.split(".")[-1]  # type: ignore
    view = parser.model.create_view(f"{view_name} Overview")
    component_obj: Object = parser.scad_id_to_scad_obj[component.id]  # type: ignore
    view.add_object(component_obj)
    if component.process:
        process = parser.scad_id_to_scad_obj[component.process.id]  # type: ignore
        view.add_object(obj=process, x=200)
    global_y: int = 200
    if component.__class__.__name__ == "Service":
        if component.foreground_service_type:  # type: ignore
            fg_svc_obj: Object = parser.scad_id_to_scad_obj[component.foreground_service_type.id]  # type: ignore
            fg_svc_grp = view.create_group(
                name=f"{view_name} foreground service type",
                icon=default_icon,
                y=global_y,
            )
            global_y += padding
            fg_svc_grp.meta["color"] = colors[1]  # type: ignore
            fg_svc_grp.meta["expand"] = True  # type: ignore
            fg_svc_grp.add_object(fg_svc_obj, 0)
            grants_component = [
                x
                for x in fg_svc_obj.connected_objects()
                if x.asset_type not in ["Service"]
            ]
            if grants_component:
                add_objects_horizontally(
                    group=fg_svc_grp, items=grants_component, padding=padding, y=200
                )
                global_y += padding
    permissions: List[Object] = []
    for attr in ["permission", "write_permission", "read_permission"]:
        if hasattr(component, attr):
            permission = getattr(component, attr)
            if not permission:
                continue
            permissions.append(
                component.manifest_parent.scad_permission_objs[permission]
            )
    if permissions:
        add_objects_horizontally(
            group=view, items=permissions, padding=padding, y=global_y  # type: ignore
        )
        global_y += padding
    intent_filters = [
        parser.scad_id_to_scad_obj[x.id] for x in component.intent_filters  # type: ignore
    ]
    if intent_filters:
        add_objects_horizontally(
            group=view,  # type: ignore
            items=intent_filters,
            padding=padding,
            y=global_y,
        )
        global_y += padding
    intent_components: Group = view.create_group(
        name=f"{view_name} Intent Components", icon=default_icon, y=global_y
    )
    intent_components.meta["expand"] = True  # type: ignore
    intent_components.meta["color"] = colors[0]  # type: ignore
    local_y: int = 0
    actions = [
        parser.scad_id_to_scad_obj[y.id]  # type: ignore
        for x in component.intent_filters
        for y in x.actions
    ]
    if actions:
        add_objects_horizontally(
            group=intent_components, items=actions, padding=padding, y=local_y
        )
        local_y += padding
    categories = [
        parser.scad_id_to_scad_obj[y.id]  # type: ignore
        for x in component.intent_filters
        for y in x.categories
    ]
    if categories:
        add_objects_horizontally(
            group=intent_components, items=categories, padding=padding, y=local_y
        )
        local_y += padding
    uris = [
        parser.scad_id_to_scad_obj[y.id]  # type: ignore
        for x in component.intent_filters
        for y in x.uris
    ]
    if uris:
        print([x.asset_type for x in uris])
        add_objects_horizontally(
            group=intent_components, items=uris, padding=padding, y=local_y
        )
        local_y += padding
    intent = parser.scad_id_to_scad_obj[component.parent.intent.id]  # type: ignore
    intent_components.add_object(obj=intent, y=local_y)


def application_view(parser: AndroidParser):
    bounding_boxes: Dict[Group, BoundingBox] = {}
    # padding = 200

    def fill_component_grp(grp: Group, components: List[AndroidComponent]) -> None:
        for idx, component in enumerate(components):
            y = idx * 200
            component_view(parser=parser, component=component)
            component_obj = parser.scad_id_to_scad_obj[component.id]  # type: ignore
            grp.add_object(obj=component_obj, y=y)
            if component_obj.__class__.__name__ == "Activity":
                pass
            if component_obj.__class__.__name__ == "BroadcastReceiver":
                pass
            if component_obj.__class__.__name__ == "Service":
                pass
            if component_obj.__class__.__name__ == "ContentProvider":
                pass

    applications: List["Application"] = [
        x.application for x in parser.manifests.values()
    ]

    for i, app in enumerate(applications):
        app_view = parser.model.create_view(f"{app.name} Overview")
        app_grp: Group = app_view.create_group(name=app.name, icon=default_icon)
        app_grp.meta["expand"] = False  # type: ignore
        app_grp.meta["color"] = colors[i % len(colors)]  # type: ignore

        app_obj: Object = parser.scad_id_to_scad_obj[app.id]  # type: ignore
        app_grp.add_object(obj=app_obj, x=0, y=0)

        bounding_boxes[app_grp] = BoundingBox(x_min=-300)
        # Permissions

        activity_grp: Group = app_view.create_group(
            name="Activities", icon=default_icon, x=-200, y=200
        )
        provider_grp: Group = app_view.create_group(
            name="Content Providers", icon=default_icon, x=-400, y=200
        )
        servicer_grp: Group = app_view.create_group(
            name="Services", icon=default_icon, x=200, y=200
        )
        receiver_grp: Group = app_view.create_group(
            name="Receivers", icon=default_icon, x=400, y=200
        )

        fill_component_grp(grp=activity_grp, components=app.activities)  # type: ignore
        fill_component_grp(grp=provider_grp, components=app.providers)  # type: ignore
        fill_component_grp(grp=servicer_grp, components=app.services)  # type: ignore
        fill_component_grp(grp=receiver_grp, components=app.receivers)  # type: ignore


def main_view(parser: AndroidParser) -> None:
    pass
    """Attacker
    if parser.attacker_object:
        try:
            sub_view.add_object(parser.attacker_object, x=global_x, y=global_y)
        except DuplicateViewObjectException as e:
            log.log(f"{e}")
    # AttackerConnections
    global_y = -600
    attacker_assocs = parser.attacker_object.connected_objects()
    for i, obj in enumerate(attacker_assocs):
        global_x += (pow(-1, i) * 200) * i
        try:
            sub_view.add_object(obj, x=global_x, y=global_y)
        except DuplicateViewObjectException as e:
            log.log(f"{e}")"""
