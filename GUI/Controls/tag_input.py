import flet as ft


class TagInput(ft.Container):
    def __init__(self,
                 tag_color: ft.Colors = ft.Colors.GREEN_300,
                 tag_height: int = 40,
                 tag_spacing: int = None,
                 hint_text: str = None,
                 hint_text_padding: int = 0,
                 scroll: ft.ScrollMode = ft.ScrollMode.AUTO,
                 auto_scroll: bool = False,
                 wrap: bool = True,
                 **kwargs
                 ):
        super().__init__(**kwargs)

        # to keep track of the tags when they are removed (so we can accurately remove the value from the self.values)
        self._tag_id = 0

        # list[(tag ID, tag text value)]
        self._values: list[tuple[int, str]] = []

        self.tag_color = tag_color
        self.tag_height = tag_height

        self.value_row = ft.Row(
            spacing=tag_spacing,
            auto_scroll=auto_scroll,
            scroll=scroll,

            expand_loose=True,
            wrap=wrap,
        )

        self.textfield = ft.TextField(
            on_submit=self._on_finish,
            # removes the border
            border_width=0,

            # removes the tiny bit of padding that is defaulted in all text fields
            content_padding=0,
            width=100,
            expand_loose=True,
            hint_text=f"{' '*hint_text_padding}{hint_text}",
        )

        # add the initial text field to the row
        self.value_row.controls.append(self.textfield)

        # setting the clip to hard edge means that anything inside of this container that goes outside the bounds gets cut off
        self.clip_behavior = ft.ClipBehavior.HARD_EDGE

        # if the user chose their own padding, then it doesn't override it. if no padding was chosen, it defaults to 5
        chosen_padding = kwargs.get("padding")
        self.padding = chosen_padding if chosen_padding is not None else 5

        self.content = self.value_row
        self.alignment = ft.Alignment(-1, -1)

        # we focus on the textfield whenever the container is clicked, so that it seems like the textfield itself is
        # expanded when it actually isn't
        self.on_click = self._focus_textfield

    def get_values(self) -> list[str]:
        """
        :returns: the current values that are inputted in the text field
        """

        # returns only the value and ignores the tag ID completely
        return [
            value for tag_id, value in self._values
        ]

    # the *args exist so that this can be used in an on_... event
    def _focus_textfield(self, *args):
        self.textfield.focus()

    def _add_tag(self, tag: ft.Container):
        """inserts a tag into the value row right before the textfield"""

        # the reason we need to .insert instead of .append is because we want the textfield to always be the last value
        self.value_row.controls.insert(-1, tag)

    def _remove_tag(self, e: ft.ControlEvent):
        """removes the tag from the viewable row and from the value list"""

        tag: ft.Container = e.control

        removed_tag_id: int = tag.data["id"]
        removed_tag_value: str = tag.data["value"]

        # removes the ID-value pair from the values list
        self._values.remove(
            (
                removed_tag_id, removed_tag_value
            )
        )

        # removes the actual control (container) from the view
        self.value_row.controls.remove(tag)

        self.update()

    def _on_finish(self, e):
        """
            this function creates a tag using the current value inside of the textfield, as well as adds it to the viewable
            row and to the value list.
        """
        value = self.textfield.value

        self._values.append(
            (
                self._tag_id, value
            )
        )

        self.textfield.value = None

        tag = ft.Container(
            width=len(value) * 9 + 30,
            content=ft.Row(
                [
                    ft.Text(value, width=len(value) * 9),
                    ft.Container(
                        content=ft.Icon(
                            ft.Icons.CLOSE,
                            size=10,
                            color=ft.Colors.BLACK,
                        ),
                    )
                ]
            ),
            alignment=ft.Alignment(-1, 0),
            padding=5,
            height=self.tag_height,
            bgcolor=self.tag_color,
            border_radius=5,
            on_click=self._remove_tag,

            # adding the ID and value so that i can easily find and remove it for the on_click event
            data={
                "id": self._tag_id,
                "value": value,
            }
        )

        self._add_tag(tag)

        # increment the ID to get unique IDs for each tag in this class instance
        self._tag_id += 1

        self.update()

        # focus back on the text field so that you don't have to click it again manually.
        # despite autofocus being on, this still needs to be here in order for it to actually focus.
        self._focus_textfield()
