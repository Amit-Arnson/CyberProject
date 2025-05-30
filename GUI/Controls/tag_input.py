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
                 max_tags: int = None,
                 max_tag_length: int = None,
                 allow_repeats: bool = True,
                 strip_tags: bool = True,
                 **kwargs
                 ):
        super().__init__(**kwargs)

        # to keep track of the tags when they are removed (so we can accurately remove the value from the self.values)
        self._tag_id = 0

        # list[(tag ID, tag text value)]
        self._values: list[tuple[int, str]] = []

        self.max_tags = max_tags
        self.allow_repeats = allow_repeats
        self.strip_tags = strip_tags

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
            width=250,
            expand_loose=True,
            hint_text=f"{' ' * hint_text_padding}{hint_text}",

            max_length=max_tag_length,

            error_style=ft.TextStyle(height=-1, color=ft.Colors.RED_800),
            on_focus=self._remove_textfield_error,
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

        self.given_border = self.border
        self.error_border = ft.border.all(color=ft.Colors.RED_800)

        # we focus on the textfield whenever the container is clicked, so that it seems like the textfield itself is
        # expanded when it actually isn't
        self.on_click = self._focus_textfield

    def clean(self) -> None:
        self.textfield.value = ""

        self.value_row.controls.clear()
        self.value_row.controls.append(self.textfield)

        self._values.clear()
        self._tag_id = 0

    def get_values(self) -> list[str]:
        """
        :returns: the current values that are inputted in the text field
        """

        # returns only the value and ignores the tag ID completely
        return [
            value for tag_id, value in self._values
        ]

    def _remove_textfield_error(self, *args):
        self.textfield.error_text = ""
        self.border = self.given_border

        self.update()

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

    @staticmethod
    def _word_to_length(word: str) -> int:
        # todo: experiment with the sizes in order to get the best fit
        letter_to_pixel_size = {
            'a': 10, 'b': 11, 'c': 9, 'd': 11, 'e': 10, 'f': 6,
            'g': 11, 'h': 11, 'i': 6, 'j': 5, 'k': 10, 'l': 6,
            'm': 16, 'n': 11, 'o': 11, 'p': 11, 'q': 11, 'r': 7,
            's': 9, 't': 6, 'u': 11, 'v': 10, 'w': 15, 'x': 10,
            'y': 10, 'z': 9,

            # Capital letters
            'A': 12, 'B': 13, 'C': 12, 'D': 13, 'E': 12, 'F': 11,
            'G': 13, 'H': 13, 'I': 6, 'J': 7, 'K': 12, 'L': 10,
            'M': 18, 'N': 14, 'O': 13, 'P': 12, 'Q': 13, 'R': 13,
            'S': 12, 'T': 11, 'U': 13, 'V': 12, 'W': 18, 'X': 12,
            'Y': 12, 'Z': 12
        }

        size = 0

        for letter in word:
            size += letter_to_pixel_size.get(letter, 10)

            # this is done so that i can easily change the size of certain "small" letters without having to change
            # the value for all of them manually
            size -= 2 if letter not in ["i", "l", "j", "f", "I"] else 1

        return size

    def _raise_textfield_error(self, error: str):
        self.textfield.error_text = error
        self.border = self.error_border

        self.update()

    def _on_finish(self, e: ft.ControlEvent):
        """
            this function creates a tag using the current value inside of the textfield, as well as adds it to the viewable
            row and to the value list.
        """
        if self.max_tags and len(self._values) >= self.max_tags:
            self._raise_textfield_error(f"max {self.max_tags} allowed")

            return

        value = self.textfield.value
        if self.strip_tags:
            value = value.strip()

        if not self.allow_repeats:
            for tag_id, tag_value in self._values:
                if tag_value == value:
                    self._raise_textfield_error(f"cannot have repeating values")

                    return

        self._values.append(
            (
                self._tag_id, value
            )
        )

        self.textfield.value = None

        value_word_length = self._word_to_length(value)

        tag = ft.Container(
            width=value_word_length + 30,
            content=ft.Row(
                [
                    ft.Text(value, width=value_word_length),
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
