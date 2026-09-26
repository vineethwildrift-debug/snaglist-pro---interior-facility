from __future__ import annotations

from pathlib import Path

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput

from android_app.main import generate_report_from_uploads


class SnaglistMobileRoot(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.padding = 24
        self.spacing = 16

        self.title = Label(text="Snaglist Pro", font_size="28sp", bold=True)
        self.add_widget(self.title)

        self.zip_input = TextInput(hint_text="ZIP path")
        self.add_widget(self.zip_input)

        self.checklist_input = TextInput(hint_text="Checklist path")
        self.add_widget(self.checklist_input)

        self.result = Label(text="Ready to generate workbook", halign="left")
        self.add_widget(self.result)

        self.generate_btn = Button(text="Generate workbook")
        self.generate_btn.bind(on_press=self.generate_report)
        self.add_widget(self.generate_btn)

    def generate_report(self, instance):
        zip_path = self.zip_input.text.strip()
        checklist_path = self.checklist_input.text.strip()

        try:
            output = generate_report_from_uploads(zip_path, checklist_path)
            self.result.text = f"Workbook ready: {Path(output).name}"
        except Exception as exc:
            self.result.text = f"Error: {exc}"


class SnaglistMobileApp(App):
    def build(self):
        return SnaglistMobileRoot()


if __name__ == "__main__":
    SnaglistMobileApp().run()
