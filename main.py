import sys

from dotenv import load_dotenv
from PySide6.QtWidgets import QApplication

from pet_window import PetWindow


def main() -> int:
    load_dotenv()

    app = QApplication(sys.argv)
    app.setApplicationName("Desktop Cat Companion")
    app.setQuitOnLastWindowClosed(False)

    pet = PetWindow()
    pet.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
