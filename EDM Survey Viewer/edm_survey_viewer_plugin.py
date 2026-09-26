import os
import json

from qgis.PyQt.QtWidgets import QDockWidget
from qgis.PyQt.QtGui import QAction
from qgis.PyQt.QtCore import Qt, QTimer

from .ui_edm_survey_viewer import EDMSurveyViewerUI
from .edm_survey_viewer_manager import EDMSurveyViewerManager

class EDMSurveyViewerPlugin:

    def __init__(self, iface):

        self.iface = iface
        self.dock = None
        self.ui = None
        self.manager = None
        self.show_panel_action = None
        
        self.date_refresh_timer = QTimer()
        self.date_refresh_timer.setInterval(2000)
        
        self.date_refresh_timer.timeout.connect(
            self.refresh_date_list_if_running
        )

    # --------------------------------------------------
    def initGui(self):

        self.ui = EDMSurveyViewerUI()
        
        self.ui.update_interval_slider.valueChanged.connect(
            self.update_refresh_interval
        )
        self.dock = QDockWidget(
            "EDM Survey Viewer",
            self.iface.mainWindow()
        )

        self.dock.setWidget(self.ui)

        self.iface.addDockWidget(
            Qt.DockWidgetArea.LeftDockWidgetArea,
            self.dock
        )

        self.ui.start_btn.clicked.connect(self.start)
        self.ui.stop_btn.clicked.connect(self.stop)

        # --------------------------------------------------
        # Plugins menu
        # --------------------------------------------------
        self.show_panel_action = QAction(
            "Show Panel",
            self.iface.mainWindow()
        )

        self.show_panel_action.setCheckable(True)
        self.show_panel_action.setChecked(True)

        self.iface.addPluginToMenu(
            "EDM Survey Viewer",
            self.show_panel_action
        )

        self.show_panel_action.toggled.connect(
            self.toggle_panel
        )

        # Keep menu state synchronised if the user
        # closes the dock using its X button
        self.dock.visibilityChanged.connect(
            self.update_panel_action
        )

        # --------------------------------------------------
        # Update table list when folder changes
        # --------------------------------------------------
        self.ui.folder_input.textChanged.connect(
            self.update_table_list
        )

        # --------------------------------------------------
        # Update dates when table changes
        # --------------------------------------------------
        self.ui.table_combo.currentTextChanged.connect(
            self.update_date_list
        )

        # --------------------------------------------------
        # Auto-refresh running session
        # --------------------------------------------------

        # User changes table
        self.ui.table_combo.activated.connect(
            self.restart_if_running
        )

        # User changes date
        self.ui.date_combo.activated.connect(
            self.restart_if_running
        )

        # User changes projection
        self.ui.projection_combo.activated.connect(
            self.restart_if_running
        )

        # User toggles greying
        self.ui.grey_old_btn.clicked.connect(
            self.restart_if_running
        )
        # User changes coordinate system mode
        # Stop the current session and wait for the user to restart
        self.ui.crs_mode_combo.activated.connect(
            self.stop_if_running
        )

        # User changes selected CRS
        # Stop the current session and wait for the user to restart
        self.ui.crs_widget.crsChanged.connect(
            self.stop_if_running
        )
        
    # --------------------------------------------------
    def update_refresh_interval(self, seconds):

        interval_ms = seconds * 1000

        self.date_refresh_timer.setInterval(
            interval_ms
        )

        if self.manager:
            self.manager.refresh_interval_ms = (
                interval_ms
            )

            self.manager.timer.setInterval(
                interval_ms
            )

    # --------------------------------------------------
    def toggle_panel(self, visible):

        if not self.dock:
            return

        self.dock.setVisible(visible)


    # --------------------------------------------------
    def update_panel_action(self, visible):

        if not self.show_panel_action:
            return

        self.show_panel_action.blockSignals(True)
        self.show_panel_action.setChecked(visible)
        self.show_panel_action.blockSignals(False)
        
    # --------------------------------------------------
    def refresh_date_list_if_running(self):

        if not self.manager:
            return

        self.update_date_list()
        
    # --------------------------------------------------
    def restart_if_running(self):

        if not self.manager:
            return

        print(
            "EDM Survey Viewer: refreshing..."
        )

        self.start()

    # --------------------------------------------------
    def stop_if_running(self):

        if not self.manager:
            return

        print(
            "EDM Survey Viewer: coordinate system changed - stopping..."
        )

        self.stop()

    # --------------------------------------------------
    def get_json_path(self):

        json_path = self.ui.folder_input.text().strip()

        if not json_path:
            return None

        if not os.path.isfile(json_path):
            return None

        if not json_path.lower().endswith(".json"):
            return None

        return json_path

    # --------------------------------------------------
    def update_table_list(self):

        json_path = self.get_json_path()

        if not json_path:
            return

        try:

            with open(
                json_path,
                "r",
                encoding="utf-8"
            ) as f:

                db = json.load(f)

            table_names = []

            for table_name, table_data in db.items():

                if table_name.lower() in (
                    "units",
                    "prisms"
                ):
                    continue

                if isinstance(table_data, dict):
                    table_names.append(
                        table_name
                    )

            self.ui.set_table_list(
                table_names
            )

            self.ui.set_database_name(
                os.path.basename(
                    json_path
                )
            )

            self.update_date_list()

        except Exception as e:

            print(
                f"EDM Survey Viewer: failed to load tables: {e}"
            )

    # --------------------------------------------------
    def update_date_list(self):

        json_path = self.get_json_path()

        if not json_path:
            return

        try:

            with open(
                json_path,
                "r",
                encoding="utf-8"
            ) as f:

                db = json.load(f)

            table_name = (
                self.ui.get_selected_table()
            )

            if table_name not in db:
                return

            table = db[table_name]

            dates = set()

            for record in table.values():

                date_value = str(
                    record.get(
                        "DATE",
                        ""
                    )
                ).strip()

                if not date_value:
                    continue

                dates.add(
                    date_value[:10]
                )

            self.ui.set_date_list(
                sorted(dates)
            )

        except Exception as e:

            print(
                f"EDM Survey Viewer: failed to load dates: {e}"
            )
    # --------------------------------------------------
    def start(self):

        json_path = self.get_json_path()

        if not json_path:

            self.iface.messageBar().pushWarning(
                "EDM Survey Viewer",
                "Invalid folder or JSON file"
            )

            return
            
        update_interval = (
            self.ui.get_update_interval()
        )
        self.date_refresh_timer.setInterval(
            update_interval * 1000
        )
        self.ui.set_database_name(
            os.path.basename(
                json_path
            )
        )

        selected_table = (
            self.ui.get_selected_table()
        )

        selected_date = (
            self.ui.get_selected_date()
        )

        selected_projection = (
            self.ui.get_selected_projection()
        )

        selected_crs = (
            self.ui.get_crs()
        )

        grey_previous_days = (
            self.ui.grey_previous_days_enabled()
        )

        # --------------------------------------------------
        # Stop existing session first
        # --------------------------------------------------
        if self.manager:
            self.manager.stop()

        self.manager = EDMSurveyViewerManager(
            json_path,
            table_name=selected_table,
            survey_date=selected_date,
            projection_mode=selected_projection,
            grey_previous_days=grey_previous_days,
            crs=selected_crs,
            canvas=self.iface.mapCanvas(),
            refresh_interval_seconds=update_interval
        )

        self.manager.start()
        self.date_refresh_timer.start()
        
        self.iface.messageBar().pushInfo(
            "EDM Survey Viewer",
            f"Started ({selected_table}, {selected_date}, {selected_projection})"
        )

    # --------------------------------------------------
    def stop(self):

        self.date_refresh_timer.stop()
        
        if self.manager:

            self.manager.stop()
            self.manager = None

        self.iface.messageBar().pushInfo(
            "EDM Survey Viewer",
            "Stopped"
        )
        
    # --------------------------------------------------
    def unload(self):

        self.stop()

        if self.show_panel_action:

            self.iface.removePluginMenu(
                "EDM Survey Viewer",
                self.show_panel_action
            )

            self.show_panel_action = None

        if self.dock:

            self.iface.removeDockWidget(
                self.dock
            )

            self.dock = None