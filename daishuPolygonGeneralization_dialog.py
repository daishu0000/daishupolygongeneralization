# -*- coding: utf-8 -*-
"""
/***************************************************************************
 DaishuPolygonGeneralizationDialog
                                 A QGIS plugin
 a polygon generalization tool developed by daishu.
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2024-11-28
        git sha              : $Format:%H$
        copyright            : (C) 2024 by daishu
        email                : daishu10000@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os

from qgis.PyQt import uic
from qgis.PyQt import QtWidgets

from qgis.core import (
    QgsWkbTypes,
    QgsRectangle,
    QgsProject,          # 用于将图层添加到项目
    QgsVectorLayer,      # 创建矢量图层
    QgsField,            # 定义属性字段
    QgsFeature,          # 创建要素
    QgsGeometry,         # 几何操作
    QgsLineString,       # 线几何类型
    QgsPointXY

)
from qgis.PyQt.QtCore import QVariant  # 用于属性字段的数据类型

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'daishuPolygonGeneralization_dialog_base.ui'))


class DaishuPolygonGeneralizationDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(DaishuPolygonGeneralizationDialog, self).__init__(parent)
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

        self.pbGeneralize.clicked.connect(self.onPbGeneralizeClicked)

    def onPbGeneralizeClicked(self):
        currLayer=self.mlLayer.currentLayer()
        crs = currLayer.crs()
        crs_auth_id = crs.authid()  # 获取参考系的 EPSG 代码，例如 "EPSG:4326"

        warningLabel=self.lblWarning
        if self.check_layer_type(currLayer,warningLabel)==1:
            if currLayer is not None and currLayer.isValid():
                # 确保图层是矢量图层
                if currLayer.geometryType() == QgsWkbTypes.PolygonGeometry:
                    bounds=self.get_layer_bounds(currLayer)
                    if bounds is None:
                        return
                    width=bounds.width()
                    height=bounds.height()

                    pic=min(width,height)/200

                    print(pic)
                    point_layer=self.generate_points(pic,currLayer,crs_auth_id)
                    self.generate_delaunay_triangulation(point_layer,crs_auth_id)
                    warningLabel.setText("生成完成")
                else:
                    print("当前图层不是面图层！")
            else:
                print("图层无效！")

    def check_layer_type(self,layer,warningLabel):

        # 获取几何类型
        wkb_type = layer.wkbType()
        geometry_type = QgsWkbTypes.geometryType(wkb_type)

        # 根据几何类型输出图层类型
        if geometry_type == QgsWkbTypes.PointGeometry:
            print("这是一个点图层")
            warningLabel.setText("不能是点图层")
        elif geometry_type == QgsWkbTypes.LineGeometry:
            print("这是一个线图层")
            warningLabel.setText("不能是线图层")
        elif geometry_type == QgsWkbTypes.PolygonGeometry:
            print("这是一个面图层")
            return 1
        else:
            print("未知类型的矢量图层")

        # 打印更详细的 WKB 信息
        wkb_name = QgsWkbTypes.displayString(wkb_type)
        print(f"详细类型：{wkb_name}")
        return 0

    def get_layer_bounds(self,layer):
        # 初始化范围变量
        total_extent = None

        # 遍历图层中的所有要素
        for feature in layer.getFeatures():
            geometry = feature.geometry()
            if geometry is not None:
                # 获取要素的范围
                bbox = geometry.boundingBox()

                # 合并范围
                if total_extent is None:
                    total_extent = QgsRectangle(bbox)
                else:
                    total_extent.combineExtentWith(bbox)

        if total_extent:
            return total_extent
        else:
            print("图层没有有效的范围")
            return None
    def generate_points(self,pic,layer,crs):
        # 创建一个临时点图层用于存放生成的点
        point_layer = QgsVectorLayer("Point?crs="+crs, "Generated Points", "memory")
        point_provider = point_layer.dataProvider()

        # 设置属性表（可选）
        point_provider.addAttributes([QgsField("polygon_id", QVariant.Int)])
        point_layer.updateFields()

        for feature in layer.getFeatures():
            geom = feature.geometry()
            if geom is None or not geom.isGeosValid():
                continue

            # 获取外环和内环
            polygons = geom.constParts()

            for polygon in polygons:

                boundary_line = polygon.boundary()
                points = list(boundary_line.vertices())

                lastPoint=None
                # 遍历边界上的每个点
                for point in points:
                    # 将 QgsPoint 转换为 QgsPointXY
                    point_xy = QgsPointXY(point)

                    if lastPoint is not None:
                        distance = lastPoint.distance(point_xy)
                        if distance>pic:
                            num_points = int(distance // pic)  # 计算需要插入的点数
                            for i in range(1, num_points + 1):
                                # 插值点按比例计算
                                interpolated_point = QgsPointXY(
                                    lastPoint.x() + (point_xy.x() - lastPoint.x()) * i / (num_points + 1),
                                    lastPoint.y() + (point_xy.y() - lastPoint.y()) * i / (num_points + 1)
                                )
                                # 创建一个 QgsFeature 并设置几何和属性
                                point_feature = QgsFeature()
                                point_feature.setGeometry(
                                    QgsGeometry.fromPointXY(interpolated_point))  # 使用 QgsPointXY 创建几何
                                point_feature.setAttributes([feature.id()])  # 设置 polygon_id 属性

                                # 将插值点添加到图层
                                point_provider.addFeature(point_feature)

                    # 创建一个 QgsFeature 并设置几何和属性
                    point_feature = QgsFeature()
                    point_feature.setGeometry(QgsGeometry.fromPointXY(point_xy))  # 使用 QgsPointXY 创建几何
                    point_feature.setAttributes([feature.id()])  # 设置 polygon_id 属性

                    # 将点添加到图层
                    point_provider.addFeature(point_feature)
                    lastPoint=point_xy
        # 将临时图层添加到地图中
        QgsProject.instance().addMapLayer(point_layer)
        print(f"生成的点已添加到图层：{point_layer.name()}")
        return point_layer

    def generate_delaunay_triangulation(self, point_layer, crs):
        # 创建一个临时图层来保存 Delaunay 三角网
        triangulation_layer = QgsVectorLayer("Polygon?crs=" + crs, "Delaunay Triangulation", "memory")
        triangulation_provider = triangulation_layer.dataProvider()

        # 添加属性字段（可选）
        triangulation_provider.addAttributes([QgsField("triangle_id", QVariant.Int)])
        triangulation_layer.updateFields()

        # 提取 point_layer 中的所有点
        points = []
        for feature in point_layer.getFeatures():
            point = feature.geometry().centroid().asPoint()  # 获取点的中心
            points.append(QgsPointXY(point.x(), point.y()))  # 获取点的 x, y 坐标

        # 创建 QgsGeometry 对象
        geometry = QgsGeometry.fromPolylineXY(points)

        # 生成 Delaunay 三角剖分
        triangulation = QgsGeometry.delaunayTriangulation(geometry)

        # 遍历 GeometryCollection 中的每个三角形并将其添加到图层
        triangle_id = 1
        for geom in triangulation.asGeometryCollection():
            if geom.type() == QgsWkbTypes.PolygonGeometry:
                # 创建一个新的要素
                feature = QgsFeature()
                feature.setGeometry(geom)

                # 设置属性字段
                feature.setAttributes([triangle_id])

                # 将要素添加到图层
                triangulation_provider.addFeature(feature)

                triangle_id += 1

        # 刷新图层以显示更改
        triangulation_layer.updateExtents()
        QgsProject.instance().addMapLayer(triangulation_layer)

