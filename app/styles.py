"""Qt stylesheets, ported from the original web UI's dark theme."""

DARK_QSS = """
QWidget { background: #07070b; color: #f7f5fc; font-family: "Segoe UI"; font-size: 12px; }
QMainWindow { background: #07070b; }

#Sidebar { background: #0b0b11; border-right: 1px solid #292834; }
#TopBar { background: #07070b; border-bottom: 1px solid #292834; }
#BottomBar { background: #07070b; border-top: 1px solid #292834; }
#Stage { background: #07070b; }
#VisualFrame { background: #09090f; border: 1px solid #292834; border-radius: 13px; }
#VisualFrame[fullscreen="true"] { border: none; border-radius: 0; }

QLabel#Brand { font-size: 16px; font-weight: 800; }
QLabel#SectionLabel { color: #aaa7b5; font-size: 10px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; }
QLabel#Desc, QLabel#Hint { color: #9895a6; font-size: 11px; }
QLabel#TitleLabel { font-size: 13px; font-weight: 800; }
QLabel#SmallMuted { color: #9895a6; font-size: 10px; }

QPushButton { background: #14141c; border: 1px solid #292834; border-radius: 9px; padding: 7px 12px; min-height: 22px; }
QPushButton:hover { border-color: #7c7690; }
QPushButton:pressed { background: #191922; }
QPushButton#Primary { background: #a995ff; color: #13101a; font-weight: 800; border: none; }
QPushButton#Primary:hover { background: #b7a8ff; }
QPushButton#Ghost { background: #111118aa; }
QPushButton#IconBtn { min-width: 30px; max-width: 34px; padding: 4px; font-size: 14px; }

QLineEdit, QComboBox { background: #14141c; border: 1px solid #292834; border-radius: 9px; padding: 6px 8px; min-height: 22px; }
QLineEdit:focus, QComboBox:focus { border-color: #a995ff; }
QComboBox QAbstractItemView { background: #14141c; selection-background-color: #a995ff33; }

QSlider::groove:horizontal { height: 4px; background: #292834; border-radius: 2px; }
QSlider::handle:horizontal { background: #a995ff; width: 14px; margin: -6px 0; border-radius: 7px; }

QCheckBox { color: #b5b2bf; font-size: 11px; spacing: 7px; }
QCheckBox::indicator { width: 15px; height: 15px; border: 1px solid #292834; border-radius: 4px; background: #14141c; }
QCheckBox::indicator:checked { background: #a995ff; border-color: #a995ff; }

QFrame#Box { border: 1px solid #292834; background: #111119; border-radius: 9px; }
QFrame#Divider { background: #292834; max-height: 1px; min-height: 1px; }

QScrollArea { border: none; }
QScrollBar:vertical { background: transparent; width: 8px; }
QScrollBar::handle:vertical { background: #292834; border-radius: 4px; min-height: 24px; }

#StatusDot[live="true"] { background: #a995ff; border-radius: 5px; }
#StatusDot[live="false"] { background: #6b6872; border-radius: 5px; }
"""

LIGHT_QSS = DARK_QSS.replace("#07070b", "#f5f4f9") \
                     .replace("#0b0b11", "#ffffff") \
                     .replace("#09090f", "#eeedf3") \
                     .replace("#14141c", "#ffffff") \
                     .replace("#191922", "#ececf3") \
                     .replace("#111118aa", "#ffffffcc") \
                     .replace("#111119", "#ffffff") \
                     .replace("#292834", "#dcdae6") \
                     .replace("#f7f5fc", "#17151f") \
                     .replace("#9895a6", "#6b6878") \
                     .replace("#aaa7b5", "#7a7788") \
                     .replace("#b5b2bf", "#4a4756")
