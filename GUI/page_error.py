import flet as ft


class PageError:
    """
        a way to easily display errors that are not related to 1 specific thing.
        this will open up an AlertDialog to display the error
    """
    def __init__(self, page: ft.Page):
        self.page = page

    def error(self, error: ft.Control):
        def close_alert(e):
            self.page.close(error_alert)

        error_alert: ft.AlertDialog = ft.AlertDialog(
            title=ft.Text("Error"),
            content=error,
            actions=[
                ft.TextButton(text="OK", on_click=close_alert),
            ],
            open=True,
            data={"error_type": "alert"}
        )

        # adds the error to the page's class "page_view" parameter (check the classes under the GUI dir for a better understanding)

        if hasattr(self.page, "view"):
            self.page.view.append_error(error_alert)
        else:
            # todo: think of a better way to handle it
            raise Exception("page has no attribute \"view\"")
