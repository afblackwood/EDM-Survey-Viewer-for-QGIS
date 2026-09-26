from qgis.PyQt.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLineEdit,
    QLabel,
    QFileDialog,
    QComboBox,
    QSlider
)
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsCoordinateReferenceSystem
from qgis.gui import QgsProjectionSelectionWidget


class EDMSurveyViewerUI(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("EDM Survey Viewer")

        layout = QVBoxLayout()

        # ------------------------------------------------------------
        # DATABASE INFO
        # ------------------------------------------------------------
        db_row = QHBoxLayout()

        self.database_label = QLabel("Database:")
        self.database_name_label = QLabel("Not connected")

        self.database_name_label.setStyleSheet(
            "font-weight: bold; color: #2c3e50;"
        )

        db_row.addWidget(self.database_label)
        db_row.addWidget(self.database_name_label)
        db_row.addStretch()

        layout.addLayout(db_row)

        # ------------------------------------------------------------
        # TABLE SELECTION
        # ------------------------------------------------------------
        table_row = QHBoxLayout()

        self.table_label = QLabel("Point Table:")

        self.table_combo = QComboBox()
        self.table_combo.addItem("points_table")

        table_row.addWidget(self.table_label)
        table_row.addWidget(self.table_combo)
        table_row.addStretch()

        layout.addLayout(table_row)

        # ------------------------------------------------------------
        # DATE FILTER
        # ------------------------------------------------------------
        date_row = QHBoxLayout()

        self.date_label = QLabel("Survey Date:")

        self.date_combo = QComboBox()
        self.date_combo.addItem("All")

        date_row.addWidget(self.date_label)
        date_row.addWidget(self.date_combo)
        date_row.addStretch()

        layout.addLayout(date_row)

        # ------------------------------------------------------------
        # GREY PREVIOUS DAYS TOGGLE
        # ------------------------------------------------------------
        self.grey_old_btn = QPushButton(
            "Grey Previous Days"
        )

        self.grey_old_btn.setCheckable(True)

        layout.addWidget(self.grey_old_btn)

        # ------------------------------------------------------------
        # UPDATE INTERVAL
        # ------------------------------------------------------------
        update_row = QHBoxLayout()

        self.update_interval_label = QLabel(
            "Update Interval:"
        )

        # Qt5 / Qt6 compatible orientation
        try:
            orientation = Qt.Orientation.Horizontal
        except AttributeError:
            orientation = Qt.Horizontal

        self.update_interval_slider = QSlider(
            orientation
        )

        self.update_interval_slider.setMinimum(1)
        self.update_interval_slider.setMaximum(10)
        self.update_interval_slider.setValue(2)
        self.update_interval_slider.setTickInterval(1)

        # Qt5 / Qt6 compatible tick position
        try:
            tick_position = QSlider.TickPosition.TicksBelow
        except AttributeError:
            tick_position = QSlider.TicksBelow

        self.update_interval_slider.setTickPosition(
            tick_position
        )

        self.update_interval_value = QLabel(
            "2 sec"
        )

        update_row.addWidget(
            self.update_interval_label
        )

        update_row.addWidget(
            self.update_interval_slider
        )

        update_row.addWidget(
            self.update_interval_value
        )

        layout.addLayout(update_row)

        self.update_interval_slider.valueChanged.connect(
            self.update_interval_changed
        )

        # ------------------------------------------------------------
        # PROJECTION MODE
        # ------------------------------------------------------------
        projection_row = QHBoxLayout()

        self.projection_label = QLabel("Projection:")

        self.projection_combo = QComboBox()

        self.projection_combo.addItems([
            "XY",
            "XZ",
            "YZ",
            "-XZ",
            "-YZ"
        ])

        projection_row.addWidget(self.projection_label)
        projection_row.addWidget(self.projection_combo)
        projection_row.addStretch()

        layout.addLayout(projection_row)

        # ------------------------------------------------------------
        # COORDINATE REFERENCE SYSTEM
        # ------------------------------------------------------------
        crs_mode_row = QHBoxLayout()

        self.crs_mode_label = QLabel("Coordinate System:")

        self.crs_mode_combo = QComboBox()
        self.crs_mode_combo.addItems([
            "Local Grid",
            "Defined CRS"
        ])

        crs_mode_row.addWidget(self.crs_mode_label)
        crs_mode_row.addWidget(self.crs_mode_combo)
        crs_mode_row.addStretch()

        layout.addLayout(crs_mode_row)

        # CRS selector
        crs_row = QHBoxLayout()

        self.crs_label = QLabel("CRS:")

        self.crs_widget = QgsProjectionSelectionWidget()

        # Default CRS shown if the user switches to Defined CRS
        default_crs = QgsCoordinateReferenceSystem(
            "EPSG:32734"
        )

        try:
            self.crs_widget.setCrs(default_crs)
        except TypeError:
            self.crs_widget.setCrs(default_crs, False)

        crs_row.addWidget(self.crs_label)
        crs_row.addWidget(self.crs_widget)

        layout.addLayout(crs_row)

        # Local Grid is the default
        self.crs_mode_combo.setCurrentText("Local Grid")

        self.crs_mode_combo.currentTextChanged.connect(
            self.update_crs_state
        )

        self.update_crs_state()

        # ------------------------------------------------------------
        # JSON FOLDER INPUT
        # ------------------------------------------------------------
        self.folder_label = QLabel("JSON Database:")

        self.folder_input = QLineEdit()
        self.folder_input.setPlaceholderText(
            "Select EDMpy .json database"
        )
        self.browse_btn = QPushButton("Select DB")
        self.start_btn = QPushButton("Start")
        self.stop_btn = QPushButton("Stop")

        layout.addWidget(self.folder_label)
        layout.addWidget(self.folder_input)
        layout.addWidget(self.browse_btn)

        # ------------------------------------------------------------
        # CONTROL BUTTONS
        # ------------------------------------------------------------
        layout.addWidget(self.start_btn)
        layout.addWidget(self.stop_btn)

        self.setLayout(layout)

        self.browse_btn.clicked.connect(
            self.browse_json_file
        )

        # ------------------------------------------------------------
        # Enable grey button only when "All" is selected
        # ------------------------------------------------------------
        self.date_combo.currentTextChanged.connect(
            self.update_grey_button_state
        )

        self.update_grey_button_state()
        
    # ------------------------------------------------------------
    # Enable CRS selector only when using a defined CRS
    # ------------------------------------------------------------
    def update_crs_state(self):

        defined = (
            self.crs_mode_combo.currentText() == "Defined CRS"
        )

        self.crs_label.setEnabled(defined)
        self.crs_widget.setEnabled(defined)
    # ------------------------------------------------------------
    # Update interval changes
    # ------------------------------------------------------------
    def update_interval_changed(self, value):

        self.update_interval_value.setText(
            f"{value} sec"
        )
    def get_update_interval(self):

        return self.update_interval_slider.value()
    # ------------------------------------------------------------
    # Browse for JSON folder
    # ------------------------------------------------------------
    def browse_json_file(self):

        json_file, _ = QFileDialog.getOpenFileName(
            self,
            "Select JSON Database",
            "",
            "JSON Files (*.json)"
        )

        if json_file:
            self.folder_input.setText(json_file)

    # ------------------------------------------------------------
    # Enable/disable grey previous days button
    # ------------------------------------------------------------
    def update_grey_button_state(self):

        enabled = (
            self.date_combo.currentText() == "All"
        )

        self.grey_old_btn.setEnabled(enabled)

        if not enabled:
            self.grey_old_btn.setChecked(False)

    # ------------------------------------------------------------
    # Update database display
    # ------------------------------------------------------------
    def set_database_name(self, database_name):
        self.database_name_label.setText(database_name)

    # ------------------------------------------------------------
    # Select table in dropdown
    # ------------------------------------------------------------
    def set_table_name(self, table_name):

        index = self.table_combo.findText(
            table_name
        )

        if index >= 0:
            self.table_combo.setCurrentIndex(index)

    # ------------------------------------------------------------
    # Populate table dropdown
    # ------------------------------------------------------------
    def set_table_list(self, table_names):

        current = self.table_combo.currentText()

        self.table_combo.clear()

        for table_name in sorted(table_names):
            self.table_combo.addItem(table_name)

        index = self.table_combo.findText(current)

        if index >= 0:
            self.table_combo.setCurrentIndex(index)

    # ------------------------------------------------------------
    # Populate date dropdown
    # ------------------------------------------------------------
    def set_date_list(self, dates):

        current = self.date_combo.currentText()

        # Prevent automatic list refresh from triggering
        # date-dependent UI behaviour while rebuilding the list
        self.date_combo.blockSignals(True)

        self.date_combo.clear()

        self.date_combo.addItem("All")

        for date in sorted(dates):
            self.date_combo.addItem(date)

        index = self.date_combo.findText(current)

        if index >= 0:
            self.date_combo.setCurrentIndex(index)
        else:
            self.date_combo.setCurrentIndex(0)

        self.date_combo.blockSignals(False)

        # Update once, after the correct selection is restored
        self.update_grey_button_state()

    # ------------------------------------------------------------
    # Get selected table
    # ------------------------------------------------------------
    def get_selected_table(self):
        return self.table_combo.currentText()

    # ------------------------------------------------------------
    # Get selected date
    # ------------------------------------------------------------
    def get_selected_date(self):
        return self.date_combo.currentText()

    # ------------------------------------------------------------
    # Grey previous days enabled?
    # ------------------------------------------------------------
    def grey_previous_days_enabled(self):
        return self.grey_old_btn.isChecked()

    # ------------------------------------------------------------
    # Get selected projection
    # ------------------------------------------------------------
    def get_selected_projection(self):
        return self.projection_combo.currentText()

    # ------------------------------------------------------------
    # Get selected CRS
    # ------------------------------------------------------------
    def get_crs(self):

        if self.crs_mode_combo.currentText() == "Local Grid":
            return None

        return self.crs_widget.crs().authid()

    # ------------------------------------------------------------
    # Set CRS programmatically
    # ------------------------------------------------------------
    def set_crs(self, epsg):

        crs = QgsCoordinateReferenceSystem(
            epsg
        )

        try:
            self.crs_widget.setCrs(crs)
        except TypeError:
            self.crs_widget.setCrs(crs, False)
