#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------- #
# Copyright (c) 2025, UChicago Argonne, LLC. All rights reserved.         #
#                                                                         #
# Copyright 2025. UChicago Argonne, LLC. This software was produced       #
# under U.S. Government contract DE-AC02-06CH11357 for Argonne National   #
# Laboratory (ANL), which is operated by UChicago Argonne, LLC for the    #
# U.S. Department of Energy. The U.S. Government has rights to use,       #
# reproduce, and distribute this software.  NEITHER THE GOVERNMENT NOR    #
# UChicago Argonne, LLC MAKES ANY WARRANTY, EXPRESS OR IMPLIED, OR        #
# ASSUMES ANY LIABILITY FOR THE USE OF THIS SOFTWARE.  If software is     #
# modified to produce derivative works, such modified software should     #
# be clearly marked, so as not to confuse it with the version available   #
# from ANL.                                                               #
#                                                                         #
# Additionally, redistribution and use in source and binary forms, with   #
# or without modification, are permitted provided that the following      #
# conditions are met:                                                     #
#                                                                         #
#     * Redistributions of source code must retain the above copyright    #
#       notice, this list of conditions and the following disclaimer.     #
#                                                                         #
#     * Redistributions in binary form must reproduce the above copyright #
#       notice, this list of conditions and the following disclaimer in   #
#       the documentation and/or other materials provided with the        #
#       distribution.                                                     #
#                                                                         #
#     * Neither the name of UChicago Argonne, LLC, Argonne National       #
#       Laboratory, ANL, the U.S. Government, nor the names of its        #
#       contributors may be used to endorse or promote products derived   #
#       from this software without specific prior written permission.     #
#                                                                         #
# THIS SOFTWARE IS PROVIDED BY UChicago Argonne, LLC AND CONTRIBUTORS     #
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT       #
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS       #
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL UChicago     #
# Argonne, LLC OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,        #
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,    #
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;        #
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER        #
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT      #
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN       #
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE         #
# POSSIBILITY OF SUCH DAMAGE.                                             #
# ----------------------------------------------------------------------- #

import io
import logging
import sys
import copy

from urllib.parse import urlencode
from typing import (
    Optional, Sequence
)

from AnyQt.QtWidgets import (
    QVBoxLayout, QMenu, QAction, QActionGroup, QGraphicsItem, QApplication
)
from AnyQt.QtGui import (
    QKeySequence, QCursor, QFont, QPainter, QPixmap, QColor, QIcon,
    QWhatsThisClickedEvent, QKeyEvent, QPalette
)
from AnyQt.QtCore import (
    Qt, QSignalMapper, QCoreApplication, QPointF, QRectF,
    QMimeData, QSettings)

from orangecanvas.document.commands import UndoCommand
from orangecanvas.document.interactions import DropHandler
from orangecanvas.registry import WidgetDescription, WidgetRegistry
from orangecanvas.document.suggestions import Suggestions
from orangecanvas.document.usagestatistics import UsageStatistics
from orangecanvas.registry.qt import whats_this_helper, QtWidgetRegistry
from orangecanvas.gui.quickhelp import QuickHelpTipEvent
from orangecanvas.gui.utils import (
    message_information, clipboard_has_format, clipboard_data
)
from orangecanvas.scheme import (
    Scheme, SchemeNode, SchemeLink,
    SchemeTextAnnotation, WorkflowEvent, SchemeArrowAnnotation
)
from orangecanvas.scheme.widgetmanager import WidgetManager
from orangecanvas.canvas.scene import CanvasScene
from orangecanvas.canvas.view import CanvasView
from orangecanvas.canvas import items
from orangecanvas.canvas.items.annotationitem import Annotation as AnnotationItem
from orangecanvas.document import interactions
from orangecanvas.document import commands
from orangecanvas.document import quickmenu

from orangecanvas.document.schemeedit import (
    MimeTypeWorkflowFragment, Pos, DuplicateOffset, UndoStack, SaveWindowGroup,
    can_insert_node,  geometry_from_annotation_item, nodes_top_left,
    copy_node, copy_link, uniquify, remove_copy_number,
    SchemeEditWidget
)

log = logging.getLogger(__name__)

class OasysSchemeEditWidget(SchemeEditWidget):

    def __init__(self, parent=None, ):
        super().__init__(parent)

        self.__modified = False
        self.__registry = None       # type: Optional[WidgetRegistry]
        self.__scheme = None         # type: Optional[Scheme]

        self.__widgetManager = None  # type: Optional[WidgetManager]
        self.__path = ""

        self.__quickMenuTriggers = SchemeEditWidget.SpaceKey | \
                                   SchemeEditWidget.DoubleClicked
        self.__openAnchorsMode = SchemeEditWidget.OpenAnchors.OnShift
        self.__emptyClickButtons = Qt.NoButton
        self.__channelNamesVisible = True
        self.__nodeAnimationEnabled = True
        self.__possibleSelectionHandler = None
        self.__possibleMouseItemsMove = False
        self.__itemsMoving = {}
        self.__contextMenuTarget = None  # type: Optional[SchemeLink]
        self.__dropTarget = None  # type: Optional[items.LinkItem]
        self.__quickMenu = None   # type: Optional[quickmenu.QuickMenu]
        self.__quickTip = ""

        self.__statistics = UsageStatistics(self)

        self.__undoStack = UndoStack(self, self.__statistics)
        self.__undoStack.cleanChanged[bool].connect(self.__onCleanChanged)
        self.__undoStack.indexIncremented.connect(self.undoCommandAdded)

        # Preferred position for paste command. Updated on every mouse button
        # press and copy operation.
        self.__pasteOrigin = QPointF(20, 20)

        # scheme node properties when set to a clean state
        self.__cleanProperties = {}

        # list of links when set to a clean state
        self.__cleanLinks = []

        # list of annotations when set to a clean state
        self.__cleanAnnotations = []

        self.__dropHandlers = ()  # type: Sequence[DropHandler]

        self.__editFinishedMapper = QSignalMapper(self)
        self.__editFinishedMapper.mappedObject.connect(
            self.__onEditingFinished
        )

        self.__annotationGeomChanged = QSignalMapper(self)

        self.__setupActions()
        self.__setupUi()

        # Edit menu for a main window menu bar.
        self.__editMenu = QMenu(self.tr("&Edit"), self)
        self.__editMenu.addAction(self.__undoAction)
        self.__editMenu.addAction(self.__redoAction)
        self.__editMenu.addSeparator()
        self.__editMenu.addAction(self.__removeSelectedAction)
        self.__editMenu.addAction(self.__duplicateSelectedAction)
        self.__editMenu.addAction(self.__copySelectedAction)
        self.__editMenu.addAction(self.__pasteAction)
        self.__editMenu.addAction(self.__selectAllAction)
        self.__editMenu.addSeparator()
        self.__editMenu.addAction(self.__newQuickTextAnnotationAction)
        self.__editMenu.addAction(self.__newQuickArrowAnnotationAction)

        # Widget context menu
        self.__widgetMenu = QMenu(self.tr("Widget"), self)
        self.__widgetMenu.addAction(self.__openSelectedAction)
        self.__widgetMenu.addSeparator()
        self.__widgetMenu.addAction(self.__renameAction)
        self.__widgetMenu.addAction(self.__removeSelectedAction)
        self.__widgetMenu.addAction(self.__duplicateSelectedAction)
        self.__widgetMenu.addAction(self.__copySelectedAction)
        self.__widgetMenu.addSeparator()
        self.__widgetMenu.addAction(self.__helpAction)

        # Widget menu for a main window menu bar.
        self.__menuBarWidgetMenu = QMenu(self.tr("&Widget"), self)
        self.__menuBarWidgetMenu.addAction(self.__openSelectedAction)
        self.__menuBarWidgetMenu.addSeparator()
        self.__menuBarWidgetMenu.addAction(self.__renameAction)
        self.__menuBarWidgetMenu.addAction(self.__removeSelectedAction)
        self.__menuBarWidgetMenu.addSeparator()
        self.__menuBarWidgetMenu.addAction(self.__helpAction)

        self.__linkMenu = QMenu(self.tr("Link"), self)
        self.__linkMenu.addAction(self.__linkEnableAction)
        self.__linkMenu.addSeparator()
        self.__linkMenu.addAction(self.__nodeInsertAction)
        self.__linkMenu.addSeparator()
        self.__linkMenu.addAction(self.__linkRemoveAction)
        self.__linkMenu.addAction(self.__linkResetAction)

        self.__suggestions = Suggestions()

    def __setupActions(self):
        self.__cleanUpAction = QAction(
            self.tr("Clean Up"), self,
            objectName="cleanup-action",
            shortcut=QKeySequence("Shift+A"),
            toolTip=self.tr("Align widgets to a grid (Shift+A)"),
            triggered=self.alignToGrid,
        )

        self.__newTextAnnotationAction = QAction(
            self.tr("Text"), self,
            objectName="new-text-action",
            toolTip=self.tr("Add a text annotation to the workflow."),
            checkable=True,
            toggled=self.__toggleNewTextAnnotation,
        )

        # Create a font size menu for the new annotation action.
        self.__fontMenu = QMenu("Font Size", self)
        self.__fontActionGroup = group = QActionGroup(
            self, triggered=self.__onFontSizeTriggered
        )

        def font(size):
            f = QFont(self.font())
            f.setPixelSize(size)
            return f

        for size in [12, 14, 16, 18, 20, 22, 24]:
            action = QAction(
                "%ipx" % size, group, checkable=True, font=font(size)
            )
            self.__fontMenu.addAction(action)

        group.actions()[2].setChecked(True)

        self.__newTextAnnotationAction.setMenu(self.__fontMenu)

        self.__newQuickTextAnnotationAction = QAction(
            self.tr("Text Annotation"), self,
            objectName="new-quick-text-annotation-action",
            toolTip=self.tr("Add a text annotation to the workflow."),
            triggered=self.__triggerNewTextAnnotation
        )

        self.__newArrowAnnotationAction = QAction(
            self.tr("Arrow"), self,
            objectName="new-arrow-action",
            toolTip=self.tr("Add a arrow annotation to the workflow."),
            checkable=True,
            toggled=self.__toggleNewArrowAnnotation,
        )

        # Create a color menu for the arrow annotation action
        self.__arrowColorMenu = QMenu("Arrow Color",)
        self.__arrowColorActionGroup = group = QActionGroup(
            self, triggered=self.__onArrowColorTriggered
        )

        def color_icon(color):
            icon = QIcon()
            for size in [16, 24, 32]:
                pixmap = QPixmap(size, size)
                pixmap.fill(QColor(0, 0, 0, 0))
                p = QPainter(pixmap)
                p.setRenderHint(QPainter.Antialiasing)
                p.setBrush(color)
                p.setPen(Qt.NoPen)
                p.drawEllipse(1, 1, size - 2, size - 2)
                p.end()
                icon.addPixmap(pixmap)
            return icon

        for color in ["#000", "#C1272D", "#662D91", "#1F9CDF", "#39B54A"]:
            icon = color_icon(QColor(color))
            action = QAction(group, icon=icon, checkable=True,
                             iconVisibleInMenu=True)
            action.setData(color)
            self.__arrowColorMenu.addAction(action)

        group.actions()[1].setChecked(True)

        self.__newArrowAnnotationAction.setMenu(self.__arrowColorMenu)

        self.__newQuickArrowAnnotationAction = QAction(
            self.tr("Arrow Annotation"), self,
            objectName="new-quick-arrow-annotation-action",
            toolTip=self.tr("Add a arrow annotation to the workflow."),
            triggered=self.__triggerNewArrowAnnotation,
        )

        self.__undoAction = self.__undoStack.createUndoAction(self)
        self.__undoAction.setShortcut(QKeySequence.Undo)
        self.__undoAction.setObjectName("undo-action")

        self.__redoAction = self.__undoStack.createRedoAction(self)
        self.__redoAction.setShortcut(QKeySequence.Redo)
        self.__redoAction.setObjectName("redo-action")

        self.__selectAllAction = QAction(
            self.tr("Select all"), self,
            objectName="select-all-action",
            toolTip=self.tr("Select all items."),
            triggered=self.selectAll,
            shortcut=QKeySequence.SelectAll
        )
        self.__openSelectedAction = QAction(
            self.tr("Open"), self,
            objectName="open-action",
            toolTip=self.tr("Open selected widget"),
            triggered=self.openSelected,
            enabled=False
        )
        self.__removeSelectedAction = QAction(
            self.tr("Remove"), self,
            objectName="remove-selected",
            toolTip=self.tr("Remove selected items"),
            triggered=self.removeSelected,
            enabled=False
        )

        shortcuts = [QKeySequence(Qt.Key_Backspace),
                     QKeySequence(Qt.Key_Delete),
                     QKeySequence("Ctrl+Backspace")]

        self.__removeSelectedAction.setShortcuts(shortcuts)

        self.__renameAction = QAction(
            self.tr("Rename"), self,
            objectName="rename-action",
            toolTip=self.tr("Rename selected widget"),
            triggered=self.__onRenameAction,
            shortcut=QKeySequence(Qt.Key_F2),
            enabled=False
        )
        if sys.platform == "darwin":
            self.__renameAction.setShortcuts([
                QKeySequence(Qt.Key_F2),
                QKeySequence(Qt.Key_Enter),
                QKeySequence(Qt.Key_Return)
            ])

        self.__helpAction = QAction(
            self.tr("Help"), self,
            objectName="help-action",
            toolTip=self.tr("Show widget help"),
            triggered=self.__onHelpAction,
            shortcut=QKeySequence("F1"),
            enabled=False,
        )
        self.__linkEnableAction = QAction(
            self.tr("Enabled"), self, objectName="link-enable-action",
            triggered=self.__toggleLinkEnabled, checkable=True,
        )

        self.__linkRemoveAction = QAction(
            self.tr("Remove"), self,
            objectName="link-remove-action",
            triggered=self.__linkRemove,
            toolTip=self.tr("Remove link."),
        )

        self.__nodeInsertAction = QAction(
            self.tr("Insert Widget"), self,
            objectName="node-insert-action",
            triggered=self.__nodeInsert,
            toolTip=self.tr("Insert widget."),
        )

        self.__linkResetAction = QAction(
            self.tr("Reset Signals"), self,
            objectName="link-reset-action",
            triggered=self.__linkReset,
        )

        self.__duplicateSelectedAction = QAction(
            self.tr("Duplicate"), self,
            objectName="duplicate-action",
            enabled=False,
            shortcut=QKeySequence("Ctrl+D"),
            triggered=self.__duplicateSelected,
        )

        self.__copySelectedAction = QAction(
            self.tr("Copy"), self,
            objectName="copy-action",
            enabled=False,
            shortcut=QKeySequence("Ctrl+C"),
            triggered=self.__copyToClipboard,
        )

        self.__pasteAction = QAction(
            self.tr("Paste"), self,
            objectName="paste-action",
            enabled=clipboard_has_format(MimeTypeWorkflowFragment),
            shortcut=QKeySequence("Ctrl+V"),
            triggered=self.__pasteFromClipboard,
        )
        QApplication.clipboard().dataChanged.connect(
            self.__updatePasteActionState
        )

        self.addActions([
            self.__newTextAnnotationAction,
            self.__newArrowAnnotationAction,
            self.__linkEnableAction,
            self.__linkRemoveAction,
            self.__nodeInsertAction,
            self.__linkResetAction,
            self.__duplicateSelectedAction,
            self.__copySelectedAction,
            self.__pasteAction
        ])

        # Actions which should be disabled while a multistep
        # interaction is in progress.
        self.__disruptiveActions = [
            self.__undoAction,
            self.__redoAction,
            self.__removeSelectedAction,
            self.__selectAllAction,
            self.__duplicateSelectedAction,
            self.__copySelectedAction,
            self.__pasteAction
        ]

        #: Top 'Window Groups' action
        self.__windowGroupsAction = QAction(
            self.tr("Window Groups"), self, objectName="window-groups-action",
            toolTip="Manage preset widget groups"
        )
        #: Action group containing action for every window group
        self.__windowGroupsActionGroup = QActionGroup(
            self.__windowGroupsAction, objectName="window-groups-action-group",
        )
        self.__windowGroupsActionGroup.triggered.connect(
            self.__activateWindowGroup
        )
        self.__saveWindowGroupAction = QAction(
            self.tr("Save Window Group..."), self,
            objectName="window-groups-save-action",
            toolTip="Create and save a new window group."
        )
        self.__saveWindowGroupAction.triggered.connect(self.__saveWindowGroup)
        self.__clearWindowGroupsAction = QAction(
            self.tr("Delete All Groups"), self,
            objectName="window-groups-clear-action",
            toolTip="Delete all saved widget presets"
        )
        self.__clearWindowGroupsAction.triggered.connect(
            self.__clearWindowGroups
        )

        groups_menu = QMenu(self)
        sep = groups_menu.addSeparator()
        sep.setObjectName("groups-separator")
        groups_menu.addAction(self.__saveWindowGroupAction)
        groups_menu.addSeparator()
        groups_menu.addAction(self.__clearWindowGroupsAction)
        self.__windowGroupsAction.setMenu(groups_menu)

        # the counterpart to Control + Key_Up to raise the containing workflow
        # view (maybe move that shortcut here)
        self.__raiseWidgetsAction = QAction(
            self.tr("Bring Widgets to Front"), self,
            objectName="bring-widgets-to-front-action",
            shortcut=QKeySequence("Ctrl+Down"),
            shortcutContext=Qt.WindowShortcut,
        )
        self.__raiseWidgetsAction.triggered.connect(self.__raiseToFont)
        self.addAction(self.__raiseWidgetsAction)

    def __setupUi(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scene = CanvasScene(self)
        scene.setItemIndexMethod(CanvasScene.NoIndex)
        self.__setupScene(scene)

        view = CanvasView(scene)
        view.setFrameStyle(CanvasView.NoFrame)
        view.setRenderHint(QPainter.Antialiasing)

        self.__view = view
        self.__scene = scene

        layout.addWidget(view)
        self.setLayout(layout)

    def __setupScene(self, scene):
        # type: (CanvasScene) -> None
        """
        Set up a :class:`CanvasScene` instance for use by the editor.

        .. note:: If an existing scene is in use it must be teared down using
            __teardownScene
        """
        scene.set_channel_names_visible(self.__channelNamesVisible)
        scene.set_node_animation_enabled(self.__nodeAnimationEnabled)
        if self.__openAnchorsMode == SchemeEditWidget.OpenAnchors.Always:
            scene.set_widget_anchors_open(True)

        scene.setFont(self.font())
        scene.setPalette(self.palette())
        scene.installEventFilter(self)

        if self.__registry is not None:
            scene.set_registry(self.__registry)
        scene.focusItemChanged.connect(self.__onFocusItemChanged)
        scene.selectionChanged.connect(self.__onSelectionChanged)
        scene.link_item_activated.connect(self.__onLinkActivate)
        scene.link_item_added.connect(self.__onLinkAdded)
        scene.node_item_activated.connect(self.__onNodeActivate)
        scene.annotation_added.connect(self.__onAnnotationAdded)
        scene.annotation_removed.connect(self.__onAnnotationRemoved)
        self.__annotationGeomChanged = QSignalMapper(self)

    def __teardownScene(self, scene):
        # type: (CanvasScene) -> None
        """
        Tear down an instance of :class:`CanvasScene` that was used by the
        editor.
        """
        # Clear the current item selection in the scene so edit action
        # states are updated accordingly.
        scene.clearSelection()

        # Clear focus from any item.
        scene.setFocusItem(None)

        # Clear the annotation mapper
        self.__annotationGeomChanged.deleteLater()
        self.__annotationGeomChanged = None
        scene.focusItemChanged.disconnect(self.__onFocusItemChanged)
        scene.selectionChanged.disconnect(self.__onSelectionChanged)
        scene.removeEventFilter(self)

        # Clear all items from the scene
        scene.blockSignals(True)
        scene.clear_scene()

    # here modification to remove the numbers from duplicates
    def newNodeHelper(self, description, title=None, position=None):
        # type: (WidgetDescription, Optional[str], Optional[Pos]) -> SchemeNode
        """
        Return a new initialized :class:`.SchemeNode`. If `title`
        and `position` are not supplied they are initialized to sensible
        defaults.
        """
        if title is None:
            change_title = QSettings().value("oasys/change_title_on_new_duplicate", 0, int) == 1

            if change_title: title = self.enumerateTitle(description.name)
            else:            title = description.name

        if position is None: position = self.nextPosition()

        return SchemeNode(description, title=title, position=position)

    def __onCleanChanged(self, clean):
        # type: (bool) -> None
        if self.isWindowModified() != (not clean):
            self.setWindowModified(not clean)
            self.modificationChanged.emit(not clean)

    def __onSelectionChanged(self):
        # type: () -> None
        nodes = self.selectedNodes()
        annotations = self.selectedAnnotations()
        links = self.selectedLinks()

        self.__renameAction.setEnabled(len(nodes) == 1)
        self.__openSelectedAction.setEnabled(bool(nodes))
        self.__removeSelectedAction.setEnabled(
            bool(nodes or annotations or links)
        )

        self.__helpAction.setEnabled(len(nodes) == 1)
        self.__renameAction.setEnabled(len(nodes) == 1)
        self.__duplicateSelectedAction.setEnabled(bool(nodes))
        self.__copySelectedAction.setEnabled(bool(nodes))

        if len(nodes) > 1:
            self.__openSelectedAction.setText(self.tr("Open All"))
        else:
            self.__openSelectedAction.setText(self.tr("Open"))

        if len(nodes) + len(annotations) + len(links) > 1:
            self.__removeSelectedAction.setText(self.tr("Remove All"))
        else:
            self.__removeSelectedAction.setText(self.tr("Remove"))

        focus = self.focusNode()
        if focus is not None:
            desc = focus.description
            tip = whats_this_helper(desc, include_more_link=True)
        else:
            tip = ""

        if tip != self.__quickTip:
            self.__quickTip = tip
            ev = QuickHelpTipEvent("", self.__quickTip,
                                   priority=QuickHelpTipEvent.Permanent)

            QCoreApplication.sendEvent(self, ev)

    def __onLinkActivate(self, item):
        link = self.scene().link_for_item(item)
        action = interactions.EditNodeLinksAction(self, link.source_node,
                                                  link.sink_node)
        action.edit_links()

    def __onLinkAdded(self, item: items.LinkItem) -> None:
        item.setFlag(QGraphicsItem.ItemIsSelectable)

    def __onNodeActivate(self, item):
        # type: (items.NodeItem) -> None
        node = self.__scene.node_for_item(item)
        QCoreApplication.sendEvent(
            node, WorkflowEvent(WorkflowEvent.NodeActivateRequest))

    def __onNodePositionChanged(self, item, pos):
        # type: (items.NodeItem, QPointF) -> None
        node = self.__scene.node_for_item(item)
        new = (pos.x(), pos.y())
        if node not in self.__itemsMoving:
            self.__itemsMoving[node] = (node.position, new)
        else:
            old, _ = self.__itemsMoving[node]
            self.__itemsMoving[node] = (old, new)

    def __onAnnotationGeometryChanged(self, item):
        # type: (AnnotationItem) -> None
        annot = self.scene().annotation_for_item(item)
        if annot not in self.__itemsMoving:
            self.__itemsMoving[annot] = (annot.geometry,
                                         geometry_from_annotation_item(item))
        else:
            old, _ = self.__itemsMoving[annot]
            self.__itemsMoving[annot] = (old,
                                         geometry_from_annotation_item(item))

    def __onAnnotationAdded(self, item):
        # type: (AnnotationItem) -> None
        log.debug("Annotation added (%r)", item)
        item.setFlag(QGraphicsItem.ItemIsSelectable)
        item.setFlag(QGraphicsItem.ItemIsMovable)
        item.setFlag(QGraphicsItem.ItemIsFocusable)

        if isinstance(item, items.ArrowAnnotation):
            pass
        elif isinstance(item, items.TextAnnotation):
            # Make the annotation editable.
            item.setTextInteractionFlags(Qt.TextEditorInteraction)

            self.__editFinishedMapper.setMapping(item, item)
            item.editingFinished.connect(
                self.__editFinishedMapper.map
            )

        self.__annotationGeomChanged.setMapping(item, item)
        item.geometryChanged.connect(
            self.__annotationGeomChanged.map
        )

    def __onAnnotationRemoved(self, item):
        # type: (AnnotationItem) -> None
        log.debug("Annotation removed (%r)", item)
        if isinstance(item, items.ArrowAnnotation):
            pass
        elif isinstance(item, items.TextAnnotation):
            item.editingFinished.disconnect(
                self.__editFinishedMapper.map
            )

        self.__annotationGeomChanged.removeMappings(item)
        item.geometryChanged.disconnect(
            self.__annotationGeomChanged.map
        )

    def __onFocusItemChanged(self, newFocusItem, oldFocusItem):
        # type: (Optional[QGraphicsItem], Optional[QGraphicsItem]) -> None

        if isinstance(oldFocusItem, items.annotationitem.Annotation):
            self.__endControlPointEdit()
        if isinstance(newFocusItem, items.annotationitem.Annotation):
            if not self.__scene.user_interaction_handler:
                self.__startControlPointEdit(newFocusItem)

    def __onEditingFinished(self, item):
        # type: (items.TextAnnotation) -> None
        """
        Text annotation editing has finished.
        """
        annot = self.__scene.annotation_for_item(item)
        assert isinstance(annot, SchemeTextAnnotation)
        content_type = item.contentType()
        content = item.content()

        if annot.text != content or annot.content_type != content_type:
            assert self.__scheme is not None
            self.__undoStack.push(
                commands.TextChangeCommand(
                    self.__scheme, annot,
                    annot.text, annot.content_type,
                    content, content_type
                )
            )

    def __toggleNewArrowAnnotation(self, checked):
        # type: (bool) -> None
        if self.__newTextAnnotationAction.isChecked():
            # Uncheck the text annotation action if needed.
            self.__newTextAnnotationAction.setChecked(not checked)

        action = self.__newArrowAnnotationAction

        if not checked:
            # The action was unchecked (canceled by the user)
            handler = self.__scene.user_interaction_handler
            if isinstance(handler, interactions.NewArrowAnnotation):
                # Cancel the interaction and restore the state
                handler.ended.disconnect(action.toggle)
                handler.cancel(interactions.UserInteraction.UserCancelReason)
                log.info("Canceled new arrow annotation")

        else:
            handler = interactions.NewArrowAnnotation(self)
            checked_action = self.__arrowColorActionGroup.checkedAction()
            handler.setColor(checked_action.data())

            handler.ended.connect(action.toggle)

            self._setUserInteractionHandler(handler)

    def __onFontSizeTriggered(self, action):
        # type: (QAction) -> None
        if not self.__newTextAnnotationAction.isChecked():
            # When selecting from the (font size) menu the 'Text'
            # action does not get triggered automatically.
            self.__newTextAnnotationAction.trigger()
        else:
            # Update the preferred font on the interaction handler.
            handler = self.__scene.user_interaction_handler
            if isinstance(handler, interactions.NewTextAnnotation):
                handler.setFont(action.font())

    def __toggleNewTextAnnotation(self, checked):
        # type: (bool) -> None
        if self.__newArrowAnnotationAction.isChecked():
            # Uncheck the arrow annotation if needed.
            self.__newArrowAnnotationAction.setChecked(not checked)

        action = self.__newTextAnnotationAction

        if not checked:
            # The action was unchecked (canceled by the user)
            handler = self.__scene.user_interaction_handler
            if isinstance(handler, interactions.NewTextAnnotation):
                # cancel the interaction and restore the state
                handler.ended.disconnect(action.toggle)
                handler.cancel(interactions.UserInteraction.UserCancelReason)
                log.info("Canceled new text annotation")

        else:
            handler = interactions.NewTextAnnotation(self)
            checked_action = self.__fontActionGroup.checkedAction()
            handler.setFont(checked_action.font())

            handler.ended.connect(action.toggle)

            self._setUserInteractionHandler(handler)

    def __onArrowColorTriggered(self, action):
        # type: (QAction) -> None
        if not self.__newArrowAnnotationAction.isChecked():
            # When selecting from the (color) menu the 'Arrow'
            # action does not get triggered automatically.
            self.__newArrowAnnotationAction.trigger()
        else:
            # Update the preferred color on the interaction handler
            handler = self.__scene.user_interaction_handler
            if isinstance(handler, interactions.NewArrowAnnotation):
                handler.setColor(action.data())

    def __triggerNewTextAnnotation(self):
        """Place a text annotation at the center of the view"""
        center = self.view().viewport().rect().center()
        center = self.view().mapToScene(center)
        rect = QRectF(0, 0, 300, 150)
        rect.moveCenter(center)
        annotation = SchemeTextAnnotation(
            (rect.x(), rect.y(), rect.width(), rect.height()),
            content_type="text/markdown",
        )
        self.addAnnotation(annotation)
        # Give edit focus
        item = self.scene().item_for_annotation(annotation)
        item.setFocus(Qt.OtherFocusReason)
        item.setSelected(True)
        item.startEdit()

    def __triggerNewArrowAnnotation(self):
        """Place an arrow annotation at the center of the view"""
        center = self.view().viewport().rect().center()
        center = self.view().mapToScene(center)

        annotation = SchemeArrowAnnotation(
            (center.x() - 100, center.y()), (center.x() + 100, center.y()),
            color=self.__arrowColorActionGroup.checkedAction().data()
        )
        self.addAnnotation(annotation)
        # Give edit focus
        item = self.scene().item_for_annotation(annotation)
        item.setFocus(Qt.OtherFocusReason)
        item.setSelected(True)

    def __onRenameAction(self):
        # type: () -> None
        """
        Rename was requested for the selected widget.
        """
        selected = self.selectedNodes()
        if len(selected) == 1:
            self.editNodeTitle(selected[0])

    def __onHelpAction(self):
        # type: () -> None
        """
        Help was requested for the selected widget.
        """
        nodes = self.selectedNodes()
        help_url = None
        if len(nodes) == 1:
            node = nodes[0]
            desc = node.description

            help_url = "help://search?" + urlencode({"id": desc.qualified_name})
            self.__showHelpFor(help_url)

    def __showHelpFor(self, help_url):
        # type: (str) -> None
        """
        Show help for an "help" url.
        """
        # Notify the parent chain and let them respond
        ev = QWhatsThisClickedEvent(help_url)
        handled = QCoreApplication.sendEvent(self, ev)

        if not handled:
            message_information(
                self.tr("Sorry there is no documentation available for "
                        "this widget."),
                parent=self)

    def __toggleLinkEnabled(self, enabled):
        # type: (bool) -> None
        """
        Link 'enabled' state was toggled in the context menu.
        """
        if self.__contextMenuTarget:
            link = self.__contextMenuTarget
            command = commands.SetAttrCommand(
                link, "enabled", enabled, name=self.tr("Set enabled"),
            )
            self.__undoStack.push(command)

    def __linkRemove(self):
        # type: () -> None
        """
        Remove link was requested from the context menu.
        """
        if self.__contextMenuTarget:
            self.removeLink(self.__contextMenuTarget)

    def __linkReset(self):
        # type: () -> None
        """
        Link reset from the context menu was requested.
        """
        if self.__contextMenuTarget:
            link = self.__contextMenuTarget
            action = interactions.EditNodeLinksAction(
                self, link.source_node, link.sink_node
            )
            action.edit_links()

    def __nodeInsert(self):
        # type: () -> None
        """
        Node insert was requested from the context menu.
        """
        if not self.__contextMenuTarget:
            return

        original_link = self.__contextMenuTarget
        source_node = original_link.source_node
        sink_node = original_link.sink_node

        def filterFunc(index):
            desc = index.data(QtWidgetRegistry.WIDGET_DESC_ROLE)
            if isinstance(desc, WidgetDescription):
                return can_insert_node(desc, original_link)
            else:
                return False

        x = (source_node.position[0] + sink_node.position[0]) / 2
        y = (source_node.position[1] + sink_node.position[1]) / 2

        menu = self.quickMenu()
        menu.setFilterFunc(filterFunc)
        menu.setSortingFunc(None)

        view = self.view()
        try:
            action = menu.exec(view.mapToGlobal(view.mapFromScene(QPointF(x, y))))
        finally:
            menu.setFilterFunc(None)

        if action:
            item = action.property("item")
            desc = item.data(QtWidgetRegistry.WIDGET_DESC_ROLE)
        else:
            return

        if can_insert_node(desc, original_link):
            statistics = self.usageStatistics()
            statistics.begin_insert_action(False, original_link)
            new_node = self.newNodeHelper(desc, position=(x, y))
            self.insertNode(new_node, original_link)
        else:
            log.info("Cannot insert node: links not possible.")

    def __duplicateSelected(self):
        # type: () -> None
        """
        Duplicate currently selected nodes.
        """
        nodedups, linkdups = self.__copySelected()
        if not nodedups:
            return

        pos = nodes_top_left(nodedups)
        self.__paste(nodedups, linkdups, pos + DuplicateOffset,
                     commandname=self.tr("Duplicate"))

    def __copyToClipboard(self):
        """
        Copy currently selected nodes to system clipboard.
        """
        cb = QApplication.clipboard()
        selected = self.__copySelected()
        nodes, links = selected
        if not nodes:
            return
        s = Scheme()
        for n in nodes:
            s.add_node(n)
        for e in links:
            s.add_link(e)
        buff = io.BytesIO()
        try:
            s.save_to(buff, pickle_fallback=True)
        except Exception:
            log.error("copyToClipboard:", exc_info=True)
            QApplication.beep()
            return
        mime = QMimeData()
        mime.setData(MimeTypeWorkflowFragment, buff.getvalue())
        cb.setMimeData(mime)
        self.__pasteOrigin = nodes_top_left(nodes) + DuplicateOffset

    def __updatePasteActionState(self):
        self.__pasteAction.setEnabled(
            clipboard_has_format(MimeTypeWorkflowFragment)
        )

    def __copySelected(self):
        """
        Return a deep copy of currently selected nodes and links between them.
        """
        scheme = self.scheme()
        if scheme is None:
            return [], []

        # ensure up to date node properties (settings)
        scheme.sync_node_properties()

        # original nodes and links
        nodes = self.selectedNodes()
        links = [link for link in scheme.links
                 if link.source_node in nodes and
                 link.sink_node in nodes]

        # deepcopied nodes and links
        nodedups = [copy_node(node) for node in nodes]
        node_to_dup = dict(zip(nodes, nodedups))
        linkdups = [copy_link(link, source=node_to_dup[link.source_node],
                              sink=node_to_dup[link.sink_node])
                    for link in links]

        return nodedups, linkdups

    def __pasteFromClipboard(self):
        """Paste a workflow part from system clipboard."""
        buff = clipboard_data(MimeTypeWorkflowFragment)
        if buff is None:
            return
        sch = Scheme()
        try:
            sch.load_from(io.BytesIO(buff), registry=self.__registry, )
        except Exception:
            log.error("pasteFromClipboard:", exc_info=True)
            QApplication.beep()
            return
        self.__paste(sch.nodes, sch.links, self.__pasteOrigin)
        self.__pasteOrigin = self.__pasteOrigin + DuplicateOffset

    # here modification to avoid progressive numbers on duplicated widgets
    def __paste(self, nodedups, linkdups, pos: Optional[QPointF] = None,
                commandname=None):
        """
        Paste nodes and links to canvas. Arguments are expected to be duplicated nodes/links.
        """
        scheme = self.scheme()
        if scheme is None:
            return

        change_title = QSettings().value("oasys/change_title_on_new_duplicate", 0, int) == 1

        if change_title:
            # find unique names for new nodes
            allnames = {node.title for node in scheme.nodes}

            for nodedup in nodedups:
                nodedup.title = uniquify(
                    remove_copy_number(nodedup.title), allnames,
                    pattern="{item} ({_})", start=1
                )
                allnames.add(nodedup.title)

        if pos is not None:
            # top left of nodedups brect
            origin = nodes_top_left(nodedups)
            delta = pos - origin
            # move nodedups to be relative to pos
            for nodedup in nodedups:
                nodedup.position = (
                    nodedup.position[0] + delta.x(),
                    nodedup.position[1] + delta.y(),
                )
        if commandname is None:
            commandname = self.tr("Paste")
        # create nodes, links
        command = UndoCommand(commandname)
        macrocommands = []
        for nodedup in nodedups:
            macrocommands.append(
                commands.AddNodeCommand(scheme, nodedup, parent=command))
        for linkdup in linkdups:
            macrocommands.append(
                commands.AddLinkCommand(scheme, linkdup, parent=command))

        statistics = self.usageStatistics()
        statistics.begin_action(UsageStatistics.Duplicate)
        self.__undoStack.push(command)
        scene = self.__scene

        # deselect selected
        selected = self.scene().selectedItems()
        for item in selected:
            item.setSelected(False)

        # select pasted
        for node in nodedups:
            item = scene.item_for_node(node)
            item.setSelected(True)

    def __startControlPointEdit(self, item):
        # type: (items.annotationitem.Annotation) -> None
        """
        Start a control point edit interaction for `item`.
        """
        if isinstance(item, items.ArrowAnnotation):
            handler = interactions.ResizeArrowAnnotation(self)
        elif isinstance(item, items.TextAnnotation):
            handler = interactions.ResizeTextAnnotation(self)
        else:
            log.warning("Unknown annotation item type %r" % item)
            return

        handler.editItem(item)
        self._setUserInteractionHandler(handler)

        log.info("Control point editing started (%r)." % item)

    def __endControlPointEdit(self):
        # type: () -> None
        """
        End the current control point edit interaction.
        """
        handler = self.__scene.user_interaction_handler
        if isinstance(handler, (interactions.ResizeArrowAnnotation,
                                interactions.ResizeTextAnnotation)) and \
                not handler.isFinished() and not handler.isCanceled():
            handler.commit()
            handler.end()

            log.info("Control point editing finished.")

    def __saveWindowGroup(self):
        # type: () -> None
        """Run a 'Save Window Group' dialog"""
        workflow = self.__scheme
        manager = self.__widgetManager
        if manager is None or workflow is None:
            return
        state = manager.save_window_state()
        presets = workflow.window_group_presets()
        items = [g.name for g in presets]
        default = [i for i, g in enumerate(presets) if g.default]
        dlg = SaveWindowGroup(
            self, windowTitle="Save Group as...")
        dlg.setWindowModality(Qt.ApplicationModal)
        dlg.setItems(items)
        if default:
            dlg.setDefaultIndex(default[0])

        def store_group():
            text = dlg.selectedText()
            default = dlg.isDefaultChecked()
            try:
                idx = items.index(text)
            except ValueError:
                idx = -1
            newpresets = [copy.copy(g) for g in presets]  # shallow copy
            newpreset = Scheme.WindowGroup(text, default, state)
            if idx == -1:
                # new group slot
                newpresets.append(newpreset)
            else:
                newpresets[idx] = newpreset

            if newpreset.default:
                idx_ = idx if idx >= 0 else len(newpresets) - 1
                for g in newpresets[:idx_] + newpresets[idx_ + 1:]:
                    g.default = False

            if idx == -1:
                text = "Store Window Group"
            else:
                text = "Update Window Group"

            self.__undoStack.push(
                commands.SetWindowGroupPresets(workflow, newpresets, text=text)
            )
        dlg.accepted.connect(store_group)
        dlg.show()
        dlg.raise_()

    def __activateWindowGroup(self, action):
        # type: (QAction) -> None
        data = action.data()  # type: Scheme.WindowGroup
        wm = self.__widgetManager
        if wm is not None:
            wm.activate_window_group(data)

    def __clearWindowGroups(self):
        # type: () -> None
        workflow = self.__scheme
        if workflow is None:
            return
        self.__undoStack.push(
            commands.SetWindowGroupPresets(
                workflow, [], text="Delete All Window Groups")
        )

    def __raiseToFont(self):
        # Raise current visible widgets to front
        wm = self.__widgetManager
        if wm is not None:
            wm.raise_widgets_to_front()