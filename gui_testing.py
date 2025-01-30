import asyncio
import random
import time
import functools
import typing

import flet as ft


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


class CooldownManager:
    def __init__(self):
        self.last_called = 0  # Store the last called time

    def cooldown(self, seconds: int):
        """
        This decorator will apply a cooldown to any method.
        """

        def decorator(func):
            @functools.wraps(func)
            def wrapper(func_self, *args, **kwargs):
                current = time.time()
                if current - self.last_called >= seconds:
                    result = func(func_self, *args, **kwargs)
                    self.last_called = current  # Update the last called time
                    return result
                else:
                    # Handle the case when the cooldown is still active
                    print(f"Cooldown active. Try again in {seconds - (current - self.last_called):.2f} seconds.")
                    return None  # You could also raise an exception if needed

            return wrapper

        return decorator


class MainPage:
    def __init__(self, page: ft.Page):
        self.page = page

        self.page.on_resized = self._page_resize

        self.file_picker = ft.FilePicker()
        self.file_picker.on_result = self._finished_picking_file

        self.file_picker_file_type = ft.FilePickerFileType.AUDIO

        self.page.overlay.append(self.file_picker)

        self.last_reached_bottom = int(time.time())

        self.square_grid_view: ft.GridView = ft.GridView(
            expand=True,
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

    async def _scroll_to_bottom(self, delay: float = 0.5):
        await asyncio.sleep(delay)

        self.square_grid_view.scroll_to(offset=-1, duration=2000, curve=ft.AnimationCurve.EASE_IN)
        self.page.scroll_to(offset=-1, duration=2000, curve=ft.AnimationCurve.EASE_IN)

    # todo: figure out the AssertionError issue
    # note: assertion error of uid is None happens when you update the page too fast.
    async def _reached_bottom(self, e: ft.OnScrollEvent):
        if e.pixels == e.max_scroll_extent:
            self.page.overlay.append(
                ft.SnackBar(
                    bgcolor=ft.Colors.BLACK,
                    content=ft.Container(
                        expand=True,
                        width=self.page.width,
                        height=self.page.height / 10,
                        bgcolor=ft.Colors.BLACK,
                        content=ft.Text("You have reached the bottom!", color=ft.Colors.WHITE)
                    ),
                    open=True,
                    duration=1000,
                )
            )

            for i in range(1, 11):
                self.square_grid_view.controls.append(
                    ft.Container(
                        content=ft.Text(f"{i}"),
                        height=self.page.height / 200,
                        width=self.page.width / 200,
                        bgcolor=random.choice([ft.Colors.AMBER, ft.Colors.GREEN, ft.Colors.YELLOW]),
                        padding=10,
                    )
                )

            try:
                if int(time.time()) - self.last_reached_bottom >= 1:
                    await asyncio.sleep(0.5)
                    self.page.update()
                    self.last_reached_bottom = int(time.time())

                    await self._scroll_to_bottom()
                else:
                    pass
            except AssertionError as e:
                print(e)
                raise e

    @staticmethod
    def _create_list(list_length: int = 60) -> ft.ListView:
        lv = ft.ListView(expand=1, spacing=10, padding=20)

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

        column2 = ft.Column(
            key="fwf",
            controls=[
                ft.Container(
                    expand_loose=True,
                    height=self.page.height / 10,
                    bgcolor=ft.Colors.ORANGE
                ),

                ft.Container(
                    expand=True,
                    content=lv
                ),

                ft.Container(
                    expand_loose=True,
                    height=self.page.height / 10,
                    bgcolor=ft.Colors.TEAL
                ),
            ]
        )

        rows = ft.Row(
            key="main_page",
            expand=True,
            controls=[
                ft.Container(
                    content=column2,
                    bgcolor=ft.Colors.GREEN,
                    expand_loose=True,
                    width=self.page.width / 10
                ),
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

        self.page.update()

    @initializer
    def start(self):
        self._make_page()


def main(page: ft.Page):
    page.has = "has"

    MainPage(page=page).start()


if __name__ == "__main__":
    ft.app(main)
