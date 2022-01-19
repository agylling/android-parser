from enum import Enum
from typing import List, Dict
from securicad.model.exceptions import (  # type: ignore pylint: disable=import-error
    DuplicateViewObjectException,
)
from android_parser.utilities.log import log

READ_FILE = None
SAVE_PATH = None

colors = ["#4287f5", "#b042f5", "#f54298", "#f52298", "#6fe240", "#6fd640", "#e6ac40"]
group_limit = 20  # Amount of groups that areallowed in a view for them to be defaulted to expand=True


class Direction(Enum):
    LEFT = 0
    RIGHT = 1
    UP = 2
    DOWN = 3


class BoundingBox:
    def __init__(self, x_min=-100, x_max=100, y_min=-100, y_max=100):
        # One item will have coordinates 0,0 : but will require 100 on each side for correct padding
        self.x_min = x_min
        self.x_max = x_max
        self.y_min = y_min
        self.y_max = y_max
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

    def correct_overlap(
        self, target: "BoundingBox", direction: "Direction", padding: int
    ):
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

    def adjust_parent_bounding_box(self, candidate: "BoundingBox"):
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


def generate_views(parser: "AzureParser"):
    main_subscription_views(parser)
    iam_user_overview(parser)
    storage_overview(parser)
    cosmos_overview(parser)
    vm_vnet_overviews(parser)
    function_app_overview(parser)
    azure_db_overview(parser)
    kubernetes_overview(parser)
    pass


def add_objects_horizontally(
    group,
    items: List["ModelObject"],
    padding: int,
    y: int = 0,
    model_view=False,
) -> BoundingBox:
    f"""Helper function to add items horizontally in a group
    Keyword arguments:\n
    \t group - A ModelView Group Object \n
    \t items - A List of ModelObjects \n
    \t padding - The distance between two objects\n
    \t y - Where in the vertical line the objects should be placed \n
    \t model_view - if group is of type "ModelView" or Groups are added to other groups
    Returns: \n
        The bounding box tuple in x-axle BoundingBox(x_min, x_max, 0, 0)
    """
    x = 0
    x_min = 0
    x_max = 0
    offset = (padding * 0.5) if len(items) % 2 == 0 else 0
    if len(items) == 1:
        if model_view:
            items[0].x = 0
            items[0].y = int(y)
        else:
            try:
                group.add_object(items[0], 0, int(y))
            except DuplicateViewObjectException as e:
                log.log(f"{e}")
        return BoundingBox(0, 0, 0, 0)
    elif len(items) % 2 == 0:
        total_x = padding * len(items)
        for i in range(0, len(items)):
            item = items[i]
            x = (offset + (total_x / -2)) + padding * ((i + 1) - 1)
            if model_view:
                item.x = int(x)
                item.y = int(y)
            else:
                try:
                    group.add_object(item, int(x), int(y))
                except DuplicateViewObjectException as e:
                    log.log(f"{e}")
            x_min = x_min if x > x_min else x
            x_max = x_max if x < x_max else x
    else:
        for i, item in enumerate(items):
            x += (pow(-1, i) * padding) * i
            if model_view:
                item.x = int(x)
                item.y = int(y)
            else:
                try:
                    group.add_object(item, int(x), int(y))
                except DuplicateViewObjectException as e:
                    log.log(f"{e}")
            x_min = x_min if x > x_min else x
            x_max = x_max if x < x_max else x
    return BoundingBox(x_min, x_max, 0, 0)


def place_service_boxes_in_view(
    bounding_boxes: Dict["NewModelGroup", "BoundingBox"], view, padding: int = 150
) -> None:
    f"""Will place the large boundingboxes representing a service in the view \n
    Keyword arguments: \n
    \t bounding_boxes - A dict containing the groups and its corresponding coordinates (BoundingBox)
    \t view - The view element to place the groups in
    \t pad - an integer override for the padding between groups
    """
    groups_added = list()
    simple_view = True if len(bounding_boxes.values()) >= group_limit else False
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
        group.x = int(x)
        group.y = int(y)
        groups_added.append(group)


def main_subscription_views(parser: "AzureParser"):
    dont_visualize = set(["Subscription"])  # Handled seperately
    for subscription in parser.subscriptions.values():
        sub_view = parser.model.create_view(subscription.name)
        if subscription.subscriptionId in parser.subscription_objects:
            sub_obj = parser.subscription_objects[subscription.subscriptionId]
            try:
                sub_view.add_object(sub_obj, x=0, y=0)
            except DuplicateViewObjectException as e:
                log.log(f"{e}")
        global_x = 0
        global_y = -800
        # Attacker
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
                log.log(f"{e}")
        # Roles
        global_x = 0
        global_y = -200
        for i, role in enumerate(parser.principal_objects):
            global_x += (pow(-1, i) * 200) * i
            role_grp = sub_view.create_group(  # icon=Role doesn't work
                role, icon="Role", x=global_x, y=global_y
            )
            role_grp.meta["expand"] = False
            role_grp.meta["color"] = colors[i % len(colors)]
