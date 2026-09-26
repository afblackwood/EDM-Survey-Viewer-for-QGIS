# version 1.0

import json
import os

from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsField,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsRuleBasedRenderer,
    QgsSingleSymbolRenderer,
    QgsSimpleLineSymbolLayer
)

from qgis.PyQt.QtCore import (
    QVariant,
    QTimer
)

from qgis.utils import iface


class EDMSurveyViewerManager:

    def __init__(
        self,
        json_file,
        table_name=None,
        survey_date="All",
        projection_mode="XY",
        grey_previous_days=False,
        crs=None,
        canvas=None,
        refresh_interval_seconds=2
    ):
        self.json_file = json_file
        self.table_name = table_name
        self.survey_date = survey_date
        self.projection_mode = projection_mode
        self.grey_previous_days = grey_previous_days
        self.crs = crs

        self.layer = None
        self.canvas = canvas

        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_once)
        self.refresh_interval_ms = (
            refresh_interval_seconds * 1000
        )

        self.last_points_snapshot = {}

        self.lines_by_id = {}
        self.line_layer = None

    # ------------------------------------------------------------
    def get_latest_date(self, points):

        dates = []

        for pt in points.values():

            date_value = str(
                pt.get("DATE", "")
            ).strip()

            if date_value:
                dates.append(
                    date_value[:10]
                )

        if not dates:
            return None

        return max(dates)

    # ------------------------------------------------------------
    def load_json(self):
        if not os.path.exists(self.json_file):
            raise Exception(f"JSON not found: {self.json_file}")

        with open(self.json_file, "r", encoding="utf-8") as f:
            return json.load(f)

    # ------------------------------------------------------------
    def get_table(self, db):

        # Use requested table if supplied and valid
        if (
            self.table_name
            and self.table_name in db
            and self.table_name.lower() not in ("units", "prisms")
            and isinstance(db[self.table_name], dict)
        ):
            return self.table_name, db[self.table_name]

        # Otherwise find first usable data table
        for table_name, table_data in db.items():

            if table_name.lower() in (
                "units",
                "prisms"
            ):
                continue

            if isinstance(table_data, dict):
                return table_name, table_data

        raise Exception(
            "No usable data table found"
        )

    # ------------------------------------------------------------
    def get_table_label(self, table_name):

        parts = table_name.split("_")

        if len(parts) >= 2:
            return parts[1][:5]

        return table_name

    # ------------------------------------------------------------
    def filter_points_by_date(self, points):

        if self.survey_date == "All":
            return points

        filtered = {}

        for pid, pt in points.items():

            date_value = str(
                pt.get("DATE", "")
            )

            # compare only day/month/year portion
            point_date = date_value[:10]

            if point_date == self.survey_date:
                filtered[pid] = pt

        return filtered
        
    # ------------------------------------------------------------
    def get_plot_coordinates(self, point):

        x = float(point.get("X", 0) or 0)
        y = float(point.get("Y", 0) or 0)
        z = float(point.get("Z", 0) or 0)

        if self.projection_mode == "XZ":
            return x, z

        elif self.projection_mode == "-XZ":
            return -x, z

        elif self.projection_mode == "YZ":
            return y, z

        elif self.projection_mode == "-YZ":
            return -y, z

        return x, y
        
    # ------------------------------------------------------------
    def normalize_point(self, pt):
        return {
            "X": float(pt.get("X", 0) or 0),
            "Y": float(pt.get("Y", 0) or 0),
            "Z": float(pt.get("Z", 0) or 0),
            "ID": str(pt.get("ID", "")).strip(),
            "SUFFIX": int(pt.get("SUFFIX") or 0),
            "CODE": str(pt.get("CODE", "")),
            "DATE": str(pt.get("DATE", ""))[:10],
        }

    # ------------------------------------------------------------
    def diff_points(self, new_points):

        new_snapshot = {}
        added = {}
        updated = {}
        removed = {}

        # Build lightweight normalized snapshot for comparison
        for pid, pt in new_points.items():
            new_snapshot[pid] = self.normalize_point(pt)

        # Find removed records
        for pid in self.last_points_snapshot:
            if pid not in new_snapshot:
                removed[pid] = self.last_points_snapshot[pid]

        # Find added / updated records
        for pid, new_pt in new_snapshot.items():

            if pid not in self.last_points_snapshot:

                # IMPORTANT:
                # return complete original JSON record
                added[pid] = new_points[pid]

            else:

                old_pt = self.last_points_snapshot[pid]

                if new_pt != old_pt:

                    # IMPORTANT:
                    # return complete original JSON record
                    updated[pid] = new_points[pid]

        self.last_points_snapshot = new_snapshot

        return added, updated, removed

    # ------------------------------------------------------------
    def create_layer(self, first_record, label):

        layer_name = f"EDMpy Survey Points ({label}) [{self.projection_mode}]"

        if self.crs:
            layer = QgsVectorLayer(
                f"Point?crs={self.crs}",
                layer_name,
                "memory"
            )
        else:
            layer = QgsVectorLayer(
                "Point",
                layer_name,
                "memory"
            )
        pr = layer.dataProvider()

        fields = []

        for k in first_record.keys():
            fields.append(QgsField(k, QVariant.String))

        fields.append(QgsField("__id__", QVariant.String))

        pr.addAttributes(fields)
        layer.updateFields()

        self.layer = layer
        QgsProject.instance().addMapLayer(layer)

    # ------------------------------------------------------------
    def create_line_layer(self, label):

        layer_name = f"EDMpy Survey Lines ({label}) [{self.projection_mode}]"

        if self.crs:
            layer = QgsVectorLayer(
                f"LineString?crs={self.crs}",
                layer_name,
                "memory"
            )
        else:
            layer = QgsVectorLayer(
                "LineString",
                layer_name,
                "memory"
            )
        pr = layer.dataProvider()

        pr.addAttributes([
            QgsField("ID", QVariant.String),
            QgsField("DATE", QVariant.String)
        ])
        layer.updateFields()

        layer.startEditing()

        self.line_layer = layer
        QgsProject.instance().addMapLayer(layer)

        self.apply_line_symbology()

    # ------------------------------------------------------------
    def safe_layer(self, layer):
        try:
            return layer is not None and layer.isValid()
        except RuntimeError:
            return False

    # ------------------------------------------------------------
    def upsert_point(self, pid, point):

        record_id = str(pid)

        x, y = self.get_plot_coordinates(point)

        geom = QgsGeometry.fromPointXY(QgsPointXY(x, y))

        expr = f"\"__id__\" = '{record_id}'"
        features = list(self.layer.getFeatures(expr))

        if not features:

            feat = QgsFeature(self.layer.fields())

            attrs = []
            for f in self.layer.fields():
                name = f.name()
                if name == "__id__":
                    attrs.append(record_id)
                else:
                    attrs.append(str(point.get(name, "")))

            feat.setGeometry(geom)
            feat.setAttributes(attrs)

            self.layer.dataProvider().addFeatures([feat])
            return

        feat = features[0]
        fid = feat.id()

        attrs = []
        for f in self.layer.fields():
            name = f.name()
            if name == "__id__":
                attrs.append(record_id)
            else:
                attrs.append(str(point.get(name, "")))

        self.layer.dataProvider().changeAttributeValues({
            fid: {i: attrs[i] for i in range(len(attrs))}
        })

        self.layer.dataProvider().changeGeometryValues({
            fid: geom
        })

    # -------------------------------------------------------------
    def get_code_values(self, points):

        codes = set()

        for pt in points.values():

            code = str(
                pt.get("CODE", "")
            ).strip()

            if code:
                codes.add(code)

        return codes

    # ------------------------------------------------------------ 
    def apply_point_symbology(self, points, latest_date = None):

        from qgis.core import (
            QgsRuleBasedRenderer,
            QgsSymbol,
            QgsSimpleMarkerSymbolLayer
        )

        from qgis.PyQt.QtGui import QColor


        field_names = [
            f.name()
            for f in self.layer.fields()
        ]

        if "CODE" not in field_names:

            symbol = QgsSymbol.defaultSymbol(
                self.layer.geometryType()
            )

            self.layer.setRenderer(
                QgsSingleSymbolRenderer(symbol)
            )

            self.layer.triggerRepaint()
            return  

        # ------------------------------------------------------------
        # colour palette
        # ------------------------------------------------------------
        colours = [
            "#e41a1c",
            "#377eb8",
            "#4daf4a",
            "#984ea3",
            "#ff7f00",
            "#ffff33",
            "#a65628",
            "#f781bf",
            "#999999",
            "#66c2a5",
            "#fc8d62",
            "#8da0cb",
            "#e78ac3",
            "#a6d854",
            "#ffd92f",
            "#e5c494"
        ]

        # ------------------------------------------------------------
        # get unique CODE values
        # ------------------------------------------------------------
        code_values = self.get_code_values(points)

        if self.layer:

            for feat in self.layer.getFeatures():

                code = str(
                    feat["CODE"]
                ).strip()

                if code:
                    code_values.add(code)

        code_values = sorted(code_values)
           
           
        colour_lookup = {}

        for i, code in enumerate(code_values):
            colour_lookup[code] = colours[
                i % len(colours)
            ]

        # ------------------------------------------------------------
        # helper
        # ------------------------------------------------------------
        def make_symbol(shape, colour):

            symbol = QgsSymbol.defaultSymbol(
                self.layer.geometryType()
            )

            symbol_layer = QgsSimpleMarkerSymbolLayer()

            symbol_layer.setColor(
                QColor(colour)
            )

            symbol_layer.setSize(2.0)

            if shape == "circle":
                symbol_layer.setShape(
                    QgsSimpleMarkerSymbolLayer.Shape.Circle
                )

            else:
                symbol_layer.setShape(
                    QgsSimpleMarkerSymbolLayer.Shape.Triangle
                )

            symbol.changeSymbolLayer(
                0,
                symbol_layer
            )

            return symbol

        # ------------------------------------------------------------
        # build rules
        # ------------------------------------------------------------
        root = QgsRuleBasedRenderer.Rule(None)

        for code, colour in colour_lookup.items():

            if latest_date:

                # --------------------------------------------------
                # CURRENT DAY (coloured)
                # --------------------------------------------------

                circle_rule = QgsRuleBasedRenderer.Rule(
                    make_symbol("circle", colour),
                    filterExp=(
                        f"\"CODE\" = '{code}' "
                        f"AND left(\"DATE\",10) = '{latest_date}' "
                        f"AND regexp_match(\"ID\", '^[0-9]+$')"
                    ),
                    label=f"{code} current"
                )

                root.appendChild(circle_rule)

                triangle_rule = QgsRuleBasedRenderer.Rule(
                    make_symbol("triangle", colour),
                    filterExp=(
                        f"\"CODE\" = '{code}' "
                        f"AND left(\"DATE\",10) = '{latest_date}' "
                        f"AND NOT regexp_match(\"ID\", '^[0-9]+$')"
                    ),
                    label=f"{code} current alpha"
                )

                root.appendChild(triangle_rule)

                # --------------------------------------------------
                # OLDER DAYS (grey)
                # --------------------------------------------------

                grey_circle = QgsRuleBasedRenderer.Rule(
                    make_symbol("circle", "#B0B0B0"),
                    filterExp=(
                        f"\"CODE\" = '{code}' "
                        f"AND left(\"DATE\",10) <> '{latest_date}' "
                        f"AND regexp_match(\"ID\", '^[0-9]+$')"
                    ),
                    label=f"{code} old"
                )

                root.appendChild(grey_circle)

                grey_triangle = QgsRuleBasedRenderer.Rule(
                    make_symbol("triangle", "#B0B0B0"),
                    filterExp=(
                        f"\"CODE\" = '{code}' "
                        f"AND left(\"DATE\",10) <> '{latest_date}' "
                        f"AND NOT regexp_match(\"ID\", '^[0-9]+$')"
                    ),
                    label=f"{code} old alpha"
                )

                root.appendChild(grey_triangle)

            else:

                # numeric IDs
                circle_rule = QgsRuleBasedRenderer.Rule(
                    make_symbol("circle", colour),
                    filterExp=(
                        f"\"CODE\" = '{code}' "
                        f"AND regexp_match(\"ID\", '^[0-9]+$')"
                    ),
                    label=f"{code} (numeric)"
                )

                root.appendChild(circle_rule)

                # alpha IDs
                triangle_rule = QgsRuleBasedRenderer.Rule(
                    make_symbol("triangle", colour),
                    filterExp=(
                        f"\"CODE\" = '{code}' "
                        f"AND NOT regexp_match(\"ID\", '^[0-9]+$')"
                    ),
                    label=f"{code} (alpha)"
                )

                root.appendChild(triangle_rule)

        renderer = QgsRuleBasedRenderer(root)

        self.layer.setRenderer(renderer)

        self.layer.triggerRepaint()


    # ------------------------------------------------------------
    def load_existing_points(self, points):

        for pid, pt in points.items():
            self.upsert_point(pid, pt)

        first = next(iter(points.values()))

        if "ID" in first:
            self.rebuild_lines(points)

    # ------------------------------------------------------------
    def rebuild_lines(self, points):

        if not self.line_layer or not self.line_layer.isValid():
            label = self.get_table_label(self.table_name)
            self.create_line_layer(label)

        self.line_layer.dataProvider().deleteFeatures(
            [f.id() for f in self.line_layer.getFeatures()]
        )

        self.lines_by_id = {}

        sorted_points = sorted(
            points.items(),
            key=lambda item: (
                str(item[1].get("ID", "")).strip(),
                int(item[1].get("SUFFIX") or 0)
            )
        )

        for pid, pt in sorted_points:

            group_id = str(
                pt.get("ID", "")
            ).strip()

            point_date = str(
                pt.get("DATE", "")
            )[:10]

            try:
                x, y = self.get_plot_coordinates(pt)
            except Exception:
                continue

            if group_id not in self.lines_by_id:

                self.lines_by_id[group_id] = {
                    "date": point_date,
                    "points": []
                }

            self.lines_by_id[group_id]["points"].append(
                (
                    int(pt.get("SUFFIX") or 0),
                    QgsPointXY(x, y)
                )
            )

        for group_id, data in self.lines_by_id.items():

            pts = data["points"]
            line_date = data["date"]

            pts.sort(key=lambda x: x[0])

            ordered_points = [
                p for _, p in pts
            ]

            if len(ordered_points) < 2:
                continue

            feat = QgsFeature(
                self.line_layer.fields()
            )

            feat.setAttribute(
                "ID",
                group_id
            )

            feat.setAttribute(
                "DATE",
                line_date
            )

            feat.setGeometry(
                QgsGeometry.fromPolylineXY(
                    ordered_points
                )
            )

            self.line_layer.dataProvider().addFeatures(
                [feat]
            )

        self.apply_line_symbology(
            points,
            self.get_latest_date(points)
            if (
                self.grey_previous_days
                and self.survey_date == "All"
            )
            else None
        )

        self.line_layer.triggerRepaint()
    # ------------------------------------------------------------
    def refresh_once(self):

        db = self.load_json()
        table_name, points = self.get_table(db)

        self.table_name = table_name

        points = self.filter_points_by_date(points)
        
        if not points:
            return
            
        first = next(iter(points.values()))

        is_datum_table = (
            "ID" not in first
        )

        if (
            not is_datum_table
            and (
                not self.line_layer
                or not self.line_layer.isValid()
            )
        ):
            label = self.get_table_label(self.table_name)
            self.create_line_layer(label)
 
        # ------------------------------------------------------------
        # Determine latest survey date once
        # ------------------------------------------------------------
        latest_date = None

        if (
            self.grey_previous_days
            and self.survey_date == "All"
        ):
            latest_date = self.get_latest_date(points)
            
        # print("LATEST DATE:", latest_date)

        if not self.safe_layer(self.layer):
            self.layer = None

        # ------------------------------------------------------------
        # Create point layer
        # ------------------------------------------------------------
        if self.layer is None:

            label = self.get_table_label(table_name)

            self.create_layer(first, label)

        added, updated, removed = self.diff_points(points)

        # ------------------------------------------------------------
        # Update point features
        # ------------------------------------------------------------
        for pid, pt in {**added, **updated}.items():
            self.upsert_point(pid, pt)

        for pid in removed:

            expr = f"\"__id__\" = '{pid}'"

            feats = list(
                self.layer.getFeatures(expr)
            )

            for f in feats:
                self.layer.dataProvider().deleteFeatures(
                    [f.id()]
                )

        # ------------------------------------------------------------
        # Rebuild symbology
        # ------------------------------------------------------------
        if (
            added
            or updated
            or removed
            or self.layer.renderer() is None
            or self.grey_previous_days
        ):
            self.apply_point_symbology(
                points,
                latest_date
            )

        # ------------------------------------------------------------
        # Rebuild lines
        # ------------------------------------------------------------

        if (
            not is_datum_table
            and (
                added
                or updated
                or removed
            )
        ):
            self.rebuild_lines(points)

        if self.canvas:
            self.canvas.refresh()
            
    # -----------------------------------------------------------------
    def apply_line_symbology(self, points=None,latest_date=None):

        from qgis.core import (
            QgsRuleBasedRenderer,
            QgsSymbol,
            QgsSimpleLineSymbolLayer
        )

        from qgis.PyQt.QtGui import QColor
        
        # print("Using latest date:", latest_date)

        # --------------------------------------------------------
        # Grey old days / red latest day
        # --------------------------------------------------------
        if latest_date:

            root = QgsRuleBasedRenderer.Rule(None)

            latest_symbol = QgsSymbol.defaultSymbol(
                self.line_layer.geometryType()
            )

            latest_layer = QgsSimpleLineSymbolLayer()
            latest_layer.setColor(
                QColor("red")
            )
            latest_layer.setWidth(0.2)

            latest_symbol.changeSymbolLayer(
                0,
                latest_layer
            )

            latest_rule = QgsRuleBasedRenderer.Rule(
                latest_symbol,
                filterExp=(
                    f"\"DATE\" = '{latest_date}'"
                ),
                label="Current Day"
            )

            root.appendChild(latest_rule)

            old_symbol = QgsSymbol.defaultSymbol(
                self.line_layer.geometryType()
            )

            old_layer = QgsSimpleLineSymbolLayer()
            old_layer.setColor(
                QColor("#B0B0B0")
            )
            old_layer.setWidth(0.15)

            old_symbol.changeSymbolLayer(
                0,
                old_layer
            )

            old_rule = QgsRuleBasedRenderer.Rule(
                old_symbol,
                filterExp=(
                    f"\"DATE\" <> '{latest_date}'"
                ),
                label="Previous Days"
            )

            root.appendChild(old_rule)

            renderer = QgsRuleBasedRenderer(
                root
            )

            self.line_layer.setRenderer(
                renderer
            )

        # --------------------------------------------------------
        # Normal mode
        # --------------------------------------------------------
        else:

            symbol = QgsSymbol.defaultSymbol(
                self.line_layer.geometryType()
            )

            symbol_layer = QgsSimpleLineSymbolLayer()

            symbol_layer.setColor(
                QColor("red")
            )

            symbol_layer.setWidth(0.2)

            symbol.changeSymbolLayer(
                0,
                symbol_layer
            )

            self.line_layer.setRenderer(
                QgsSingleSymbolRenderer(symbol)
            )

        self.line_layer.triggerRepaint()
    # ------------------------------------------------------------
    def start(self):

        print("Loading initial dataset...")
        self.refresh_once()

        print("Initial load complete. Starting live updates...")

        self.timer.start(self.refresh_interval_ms)

    # ------------------------------------------------------------
    def stop(self):
        self.timer.stop()
        print("EDM Survey Viewer Stopped.")

        project = QgsProject.instance()

        # ------------------------------------------------------------
        # remove point layer
        # ------------------------------------------------------------
        if self.layer:
            try:
                project.removeMapLayer(self.layer.id())
            except Exception:
                pass
            self.layer = None

        # ------------------------------------------------------------
        # remove line layer
        # ------------------------------------------------------------
        if self.line_layer:
            try:
                project.removeMapLayer(self.line_layer.id())
            except Exception:
                pass
            self.line_layer = None

        # ------------------------------------------------------------
        # reset internal state (IMPORTANT)
        # ------------------------------------------------------------
        self.last_points_snapshot = {}
        self.lines_by_id = {}