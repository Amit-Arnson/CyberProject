import asyncio
import random
import time
import functools
import typing

import flet as ft
from GUI.Controls.navigation_sidebar import NavigationSidebar


class SimpleClicker:
    def __init__(self, page: ft.Page):
        self.page = page

        self.page.clean()

        self.page.title = "Flet counter example"
        self.page.vertical_alignment = ft.MainAxisAlignment.CENTER

        self.txt_number = ft.TextField(value="0", text_align=ft.TextAlign.RIGHT, width=100)

    def minus_click(self, e):
        self.txt_number.value = str(int(self.txt_number.value) - 1)
        self.page.update()

    def plus_click(self, e):
        self.txt_number.value = str(int(self.txt_number.value) + 1)
        self.txt_number.error_text = self.txt_number.value
        self.page.update()

    def show(self):
        self.page.add(
            ft.Row(
                [
                    ft.IconButton(ft.Icons.REMOVE, on_click=self.minus_click),
                    self.txt_number,
                    ft.IconButton(ft.Icons.ADD, on_click=self.plus_click),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
            )
        )

        print(self.page.has)


class TextBox:
    def __init__(self, page: ft.Page):
        self.page = page

        self.text = ft.TextField(
            width=100,
            label="username",
            height=50,
        )

        self.error_button = ft.Button(
            on_click=self._error_text,
            width=50,
            height=50,
            bgcolor=ft.Colors.YELLOW,
            text="f"
        )

        self.column = ft.Column(
            [
                self.text,
                self.error_button
            ]
        )

    def _error_text(self, e):
        self.text.error_text = "error!!"

        self.page.update()

    def show(self):
        self.page.add(self.column)
        self.page.update()


class SimpleContainer(ft.Container):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.height = 100
        self.width = 100

        self.bgcolor = self._generate_random_color()

        self.on_click = self._on_click

    def _generate_random_color(self):
        return random.choice(
            [
                ft.Colors.RED_100,
                ft.Colors.GREEN,
                ft.Colors.YELLOW,
                ft.Colors.BLUE
            ]
        )

    def _on_click(self, e: ft.ControlEvent):
        print("hi")

class MainPage:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.auto_scroll = False

        self.page.on_resized = self._page_resize

        self.file_picker = ft.FilePicker()
        self.file_picker.on_result = self._finished_picking_file

        self.file_picker_file_type = ft.FilePickerFileType.AUDIO

        self.page.overlay.append(self.file_picker)

        self.last_reached_bottom = int(time.time())
        self.last_scroll_direction: str = ""

        self.square_grid_view: ft.GridView = ft.GridView(
            runs_count=5,
            max_extent=150,
            child_aspect_ratio=1.0,
            spacing=5,
            run_spacing=5,
            padding=10,
            on_scroll=self._reached_bottom,

            auto_scroll=False,
        )

    def _finished_picking_file(self, e):
        print(e)

    # todo: figure out the AssertionError issue
    # note: assertion error of uid is None happens when you update the page too fast.
    async def _reached_bottom(self, e: ft.OnScrollEvent):
        current_scroll_direction = e.direction

        if current_scroll_direction:
            self.last_scroll_direction = current_scroll_direction

        if e.pixels == e.max_scroll_extent and self.last_scroll_direction == "reverse":
            self.last_scroll_direction = None
            # self.page.overlay.append(
            #     ft.SnackBar(
            #         bgcolor=ft.Colors.BLACK,
            #         content=ft.Container(
            #             expand=True,
            #             width=self.page.width,
            #             height=self.page.height / 10,
            #             bgcolor=ft.Colors.BLACK,
            #             content=ft.Text("You have reached the bottom!", color=ft.Colors.WHITE)
            #         ),
            #         open=True,
            #         duration=1000,
            #     )
            # )

            self.square_grid_view.auto_scroll = True

            for i in range(1, 11):
                self.square_grid_view.controls.append(
                    SimpleContainer(
                        content=ft.Text(f"{i}"),
                        padding=10,
                    )
                )

            try:
                if int(time.time()) - self.last_reached_bottom >= 0.5:
                    await asyncio.sleep(0.1)
                    self.page.update()
                    self.last_reached_bottom = int(time.time())
                else:
                    pass
            except AssertionError as e:
                print(e)
                raise e

    @staticmethod
    def _create_list(list_length: int = 60) -> ft.ListView:
        lv = ft.ListView(expand=1, spacing=10, padding=20, auto_scroll=False)

        for i in range(1, list_length + 1):
            lv.controls.append(ft.Text(f"Line {i}"))

        return lv

    def _add_to_grid(self, grid_item_amount: int = 120) -> None:

        for i in range(1, grid_item_amount + 1):
            self.square_grid_view.controls.append(
                ft.Container(
                    content=ft.Text(f"{i}"),
                    height=self.page.height / 200,
                    width=self.page.width / 200,
                    bgcolor=ft.Colors.AMBER,
                    padding=10,
                    on_click=lambda _: self.square_grid_view.scroll_to(delta=100)
                )
            )

    def _page_resize(self, e):
        self.start()

    def _clean(self):
        self.page.clean()

    # Custom decorator to call self._clean before executing the function
    @staticmethod
    def initializer(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            self._clean()  # Call _clean before the original function
            return func(self, *args, **kwargs)

        return wrapper

    def get_by_key(self, key: str, parent=None) -> ft.Control:

        if not parent:
            parent = self.page.controls

        for control in parent:
            if control.__getattribute__("key") == key:
                return control

    def get_key_recursive(self, key: str, controls=None) -> ft.Control | ft.Container | None:
        if controls is None:
            controls = self.page.controls  # Start from the root controls of the page

        # Iterate through the controls and check for the matching key
        for control in controls:
            if control.key == key:
                return control  # Return the control if key matches

            # If the control has child controls, search them recursively
            if hasattr(control, 'controls') and control.controls:
                result = self.get_key_recursive(key, control.controls)
                if result:
                    return result  # Return the found control

            # check for "content" attribute (things that will have "content": Containers, ...)
            elif hasattr(control, "content") and control.content:
                result = self.get_key_recursive(key, [control.content])
                if result:
                    return result

        return None  # Return None if no control is found with the given key

    def _make_page(self):
        lv = self._create_list()
        self._add_to_grid()

        column1 = ft.Column(
            key="main_column",
            auto_scroll=False,
            controls=[
                ft.Container(
                    expand_loose=True,
                    height=self.page.height / 5,
                    bgcolor=ft.Colors.TEAL,
                    on_click=lambda _: self.file_picker.pick_files(
                        file_type=self.file_picker_file_type
                    )
                ),
                ft.Container(
                    expand=True,
                    content=self.square_grid_view,
                    key="grid_viewer",
                ),
            ]
        )

        sidebar = NavigationSidebar(page=self.page)

        rows = ft.Row(
            key="main_page",
            expand=True,
            auto_scroll=False,
            controls=[
                sidebar,
                ft.Container(
                    key="main_column1",
                    content=column1,
                    bgcolor=ft.Colors.RED,
                    expand=True
                )
            ]
        )

        self.page.add(rows)
        print(self.get_key_recursive("grid_viewer"))

        # self.page.auto_scroll = False
        self.page.update()

    @initializer
    def start(self):
        self._make_page()


def main(page: ft.Page):
    page.has = "has"

    MainPage(page=page).start()


if __name__ == "__main__":
    ft.app(main)
