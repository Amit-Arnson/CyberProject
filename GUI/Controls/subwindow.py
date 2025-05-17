import typing

import flet as ft


class SubWindow(ft.GestureDetector):
    def __init__(self,
                 radius: int = 10,
                 width: int = 100,
                 height: int = 100,
                 on_close: typing.Callable = None,
                 **kwargs):
        super().__init__(**kwargs)

        self.on_close = on_close

        self.move_gesture = ft.GestureDetector(
            content=ft.Container(
                expand=True,
                expand_loose=True,
                bgcolor=ft.Colors.WHITE
            ),
            mouse_cursor=ft.MouseCursor.MOVE,
            on_vertical_drag_update=self.__on_drag_update,
            drag_interval=10,
        )

        self.content = ft.Stack(
            [
                ft.Container(
                    padding=15,
                    content=self.move_gesture,
                    bgcolor=ft.Colors.WHITE,
                    border_radius=radius
                ),
                ft.Container(
                    height=25,
                    expand=True,
                    expand_loose=True,
                    bgcolor=ft.Colors.GREY_300,
                    border_radius=ft.BorderRadius(
                        top_right=radius,
                        top_left=radius,
                        bottom_left=0,
                        bottom_right=0
                    )
                ),
                ft.Container(
                    width=50,
                    height=25,
                    bgcolor=ft.Colors.GREY_400,
                    content=ft.Icon(ft.Icons.CLOSE, color=ft.Colors.BLACK),
                    on_click=self._close,
                    right=1,
                    border_radius=ft.BorderRadius(
                        top_right=radius,
                        top_left=0,
                        bottom_left=0,
                        bottom_right=0
                    )
                )
            ],
        )
        self.mouse_cursor = ft.MouseCursor.RESIZE_UP_RIGHT_DOWN_LEFT

        self.width = width
        self.height = height

        # self.width/height update when scaled, we need the original unchanged value for __on_scale_update
        self.original_width = self.width
        self.original_height = self.height

        self.left = 0.5
        self.top = 0.5
        self.on_scale_update = self.__on_scale_update

    def set_content(self, control: ft.Control | ft.Container):
        self.move_gesture.content = control

    def _close(self, *args):
        if hasattr(self.parent, "controls"):
            self.parent.controls.remove(self)

        self.parent.update()

        if self.on_close:
            self.on_close()

    def __on_drag_update(self, e: ft.DragUpdateEvent):
        self.top = max(0, self.top + int(e.delta_y))
        self.left = max(0, self.left + int(e.delta_x))

        self.update()

    def __on_scale_update(self, event: ft.ScaleUpdateEvent):
        new_width = event.control.width + event.focal_point_delta_x
        new_height = event.control.height + event.focal_point_delta_y

        if new_width < self.original_width or new_height < self.original_height:
            return

        # todo: fix the issues with scaling from left/top
        # is_scaling_from_left = event.local_focal_point_x < event.control.width / 2
        # is_scaling_from_top = event.local_focal_point_y < event.control.height / 2
        #
        # if is_scaling_from_left:
        #     event.control.left -= event.focal_point_delta_x
        #
        # if is_scaling_from_top:
        #     event.control.top -= event.focal_point_delta_y

        # Update size
        event.control.width = new_width
        event.control.height = new_height

        event.control.update()
