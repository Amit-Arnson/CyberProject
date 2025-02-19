import flet as ft

from encryptions import EncryptedTransport
from pseudo_http_protocol import ClientMessage

from GUI.navigation_sidebar import NavigationSidebar


class TagInput(ft.Container):
    def __init__(self, tag_color: ft.Colors = ft.Colors.GREEN_300, tag_height: int = 40, tag_spacing: int = None, **kwargs):
        super().__init__(**kwargs)

        # to keep track of the tags when they are removed (so we can accurately remove the value from the self.values)
        self.tag_id = 0

        self.tag_color = tag_color
        self.tag_height = tag_height

        # list[(tag ID, tag text value)]
        self.values: list[tuple[int, str]] = []

        self.value_row = ft.Row(
            spacing=tag_spacing
        )

        self.textfield = ft.TextField(
            on_submit=self.on_finish,
            # removes the border
            border_width=0,

            # removes the tiny bit of padding that is defaulted in all text fields
            content_padding=0,

            autofocus=True,
        )

        # setting the clip to hard edge means that anything inside of this container that goes outside the bounds gets cut off
        self.clip_behavior = ft.ClipBehavior.HARD_EDGE

        # if the user chose their own padding, then it doesn't override it. if no padding was chosen, it defaults to 5
        chosen_padding = kwargs.get("padding")
        self.padding = chosen_padding if chosen_padding is not None else 5

        self.content = ft.Row(
            [
                self.value_row,
                self.textfield
            ],
            spacing=tag_spacing,
        )

    def get_values(self) -> list[str]:
        """
        :returns: the current values that are inputted in the text field
        """

        # returns only the value and ignores the tag ID completely
        return [
            value for tag_id, value in self.values
        ]

    def _remove_tag(self, e: ft.ControlEvent):
        tag: ft.Container = e.control

        removed_tag_id: int = tag.data["id"]
        removed_tag_value: str = tag.data["value"]

        # removes the ID-value pair from the values list
        self.values.remove(
            (
                removed_tag_id, removed_tag_value
            )
        )

        # removes the actual control (container) from the view
        self.value_row.controls.remove(tag)

        self.update()

    def on_finish(self, e):
        value = self.textfield.value

        self.values.append(
            (
                self.tag_id, value
            )
        )

        self.textfield.value = None

        tag = ft.Container(
            content=ft.Row(
                [
                    ft.Text(value),
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
                "id": self.tag_id,
                "value": value,
            }
        )

        self.value_row.controls.append(tag)

        # increment the ID to get unique IDs for each tag in this class instance
        self.tag_id += 1

        self.update()

        # focus back on the text field so that you don't have to click it again manually.
        # despite autofocus being on, this still needs to be here in order for it to actually focus.
        self.textfield.focus()


class UploadPage:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.padding = 0
        self.page.theme_mode = ft.ThemeMode.LIGHT

        self.page_width = 1200
        self.page_height = 700

        self.transport: EncryptedTransport | None = None
        if hasattr(page, "transport"):
            self.transport: EncryptedTransport = page.transport

        self.sidebar = NavigationSidebar()

        self.file_picker = ft.FilePicker()
        self.file_picker.on_result = self._on_finish_select

        # add the file picker control to the page
        self.page.overlay.append(self.file_picker)

        self._initialize_controls()

    def _initialize_sidebar_top(self):
        self.sidebar.top_part.margin = ft.Margin(top=10, bottom=0, right=0, left=0)

        self.sidebar.top_part.content = ft.Container(
            ft.Stack(
                [
                    ft.Container(
                        width=90,
                        height=75,
                        bgcolor=ft.Colors.BLUE_900,
                        shape=ft.BoxShape.CIRCLE,
                        right=-1,
                    ),
                    ft.Container(
                        width=320,
                        # this is the closest ive managed to make it look like 1 piece
                        height=75.19,
                        bgcolor=ft.Colors.BLUE_900,
                        left=0,
                        content=ft.Text(
                            "Upload Song", size=25, color=ft.Colors.BLUE_700,
                            weight=ft.FontWeight.BOLD
                        ),
                        alignment=ft.Alignment(0, 0)
                    ),
                ]
            ),
            width=500,
            height=100,
        )

    def _select_sound_files(self, e: ft.ControlEvent):
        self.file_picker.pick_files(
            allow_multiple=False,
            file_type=ft.FilePickerFileType.AUDIO
        )

    def _select_image_files(self, e: ft.ControlEvent):
        self.file_picker.pick_files(
            allow_multiple=True,
            file_type=ft.FilePickerFileType.IMAGE
        )

    def _on_finish_select(self, e: ft.FilePickerUploadEvent):
        print(e)

    def _initialize_file_selectors(self):
        self.song_selector = ft.Container(
            on_click=self._select_sound_files,
            width=100,
            height=50,
            bgcolor=ft.Colors.RED
        )

        self.sheet_selector = ft.Container(
            on_click=self._select_image_files,
            width=100,
            height=50,
            bgcolor=ft.Colors.GREY
        )

    def _initialize_song_info_textbox(self):
        self.song_name_textbox = ft.TextField(
            label="song name",
        )

        self.song_album_textbox = ft.TextField(
            label="song album",
        )

        # self.song_band_textbox = ft.TextField(
        #     label="song band",
        # )

        self.song_band_textbox = TagInput(
            border_radius=5,
            border=ft.border.all(color=ft.Colors.BLACK),
            padding=ft.Padding(
                right=0, top=0, bottom=0, left=2
            ),
            tag_spacing=4,
        )

    def _initialize_genre_tag_textbox(self):
        self.selected_genres_textbox = ft.TextField(
            label="genres",
        )

    def _initialize_description_textbox(self):
        self.description_textbox = ft.TextField(
            label="description",
        )

    def _initialize_controls(self):
        self._initialize_sidebar_top()

        self._initialize_file_selectors()
        self._initialize_song_info_textbox()
        self._initialize_description_textbox()
        self._initialize_genre_tag_textbox()

        # this is just a temporary container so that something takes that space up
        aa = ft.Container(
            expand=True,
            content=ft.Column(
                [
                    self.song_selector,
                    self.sheet_selector,
                    self.song_name_textbox,
                    self.song_album_textbox,
                    self.song_band_textbox,
                    self.description_textbox,
                    self.selected_genres_textbox
                ]
            )
        )

        self.page_view = ft.Row(
            [
                self.sidebar,
                aa,
            ],
            spacing=0,
            expand=True
        )

    def show(self, clear: bool = True):
        """:param clear: whether to clear the page before trying to add the page's content or not."""

        if clear:
            self.page.clean()

        self.page.view = self
        self.page.add(self.page_view)

        self.page.update()


def main(page: ft.Page):
    UploadPage(page=page).show()


if __name__ == "__main__":
    ft.app(main, assets_dir="Assets")
