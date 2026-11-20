import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

ApplicationWindow {
    id: root
    width: 1320
    height: 720
    minimumWidth: 980
    minimumHeight: 500
    visible: true
    title: "Extrator de Boletos"
    color: Theme.t.background

    readonly property var statusTexto: ({
        pending: "Na fila", success: "Sucesso", invalid: "Inválido",
        review: "Revisar", error: "Erro"
    })

    readonly property var colunas: [
        { t: "STATUS", w: 92 }, { t: "ARQUIVO", w: 170 }, { t: "EMISSOR", w: 150 },
        { t: "VENCIMENTO", w: 100 }, { t: "VALOR", w: 110 },
        { t: "LINHA DIGITÁVEL", w: -1 }, { t: "", w: 90 }
    ]

    Component.onCompleted: codigoInput.forceActiveFocus()

    Shortcut {
        sequence: "Ctrl+L"
        onActivated: { codigoInput.forceActiveFocus(); codigoInput.selectAll() }
    }

    // ---------- Componentes temáticos ----------
    component ThemedText: Text {
        property var estilo: Theme.t.body
        color: estilo.color
        font.family: estilo.font.family
        font.pixelSize: estilo.font.pixelSize
        font.weight: estilo.font.weight
        elide: Text.ElideRight
    }

    component ThemedButton: Button {
        id: btn
        property bool secundario: false
        readonly property var s: secundario ? Theme.t.buttonSecondary : Theme.t.button
        hoverEnabled: true
        focusPolicy: Qt.NoFocus  // não rouba o foco da caixa do leitor
        font.family: s.font.family
        font.pixelSize: s.font.pixelSize
        font.weight: s.font.weight
        contentItem: Text {
            text: btn.text
            font: btn.font
            color: btn.s.text
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            implicitWidth: 120
            implicitHeight: 38
            radius: btn.s.radius
            color: btn.down ? btn.s.backgroundPressed
                 : btn.hovered ? btn.s.backgroundHover : btn.s.background
            Behavior on color { ColorAnimation { duration: 120 } }
        }
        opacity: enabled ? 1 : 0.45
    }

    component ThemedInput: TextField {
        id: campo
        color: Theme.t.input.text
        placeholderTextColor: Theme.t.input.placeholder
        font.family: Theme.t.input.font.family
        font.pixelSize: Theme.t.input.font.pixelSize
        font.weight: Theme.t.input.font.weight
        leftPadding: 12
        background: Rectangle {
            implicitHeight: 38
            radius: Theme.t.input.radius
            color: Theme.t.input.background
            border.width: campo.activeFocus ? 2 : 1
            border.color: campo.activeFocus ? Theme.t.input.borderFocus : Theme.t.input.border
        }
    }

    component StatusPill: Rectangle {
        property string status: "pending"
        implicitWidth: 92
        implicitHeight: 24
        radius: 12
        color: Qt.alpha(Theme.t.status[status], 0.18)
        border.color: Theme.t.status[status]
        Text {
            anchors.centerIn: parent
            text: root.statusTexto[parent.status]
            color: Theme.t.status[parent.status]
            font.family: Theme.t.table.headerFont.family
            font.pixelSize: 12
            font.weight: 700
        }
    }

    // ---------- Diálogos ----------
    FileDialog {
        id: abrirDialog
        title: "Selecionar boletos"
        fileMode: FileDialog.OpenFiles
        nameFilters: ["Boletos (*.pdf *.png *.jpg *.jpeg)"]
        onAccepted: viewModel.adicionarArquivos(selectedFiles)
    }

    FileDialog {
        id: exportarDialog
        title: "Exportar resultados"
        fileMode: FileDialog.SaveFile
        defaultSuffix: "csv"
        nameFilters: ["CSV (*.csv)"]
        onAccepted: viewModel.exportarCsv(selectedFile)
    }

    Dialog {
        id: configDialog
        modal: true
        anchors.centerIn: parent
        width: 480
        padding: 24
        onClosed: codigoInput.forceActiveFocus()
        background: Rectangle {
            color: Theme.t.surface
            radius: 12
            border.color: Theme.t.border
        }

        ColumnLayout {
            anchors.fill: parent
            spacing: 16

            ThemedText { text: "Configurações"; estilo: Theme.t.title }
            ThemedText { text: "Aparência"; estilo: Theme.t.subtitle }

            ComboBox {
                id: temaCombo
                Layout.fillWidth: true
                model: Theme.opcoes
                textRole: "nome"
                valueRole: "id"
                Component.onCompleted: currentIndex = indexOfValue(Theme.selecionado)
                onActivated: Theme.selecionar(currentValue)

                contentItem: Text {
                    leftPadding: 12
                    text: temaCombo.displayText
                    color: Theme.t.input.text
                    font.family: Theme.t.input.font.family
                    font.pixelSize: Theme.t.input.font.pixelSize
                    verticalAlignment: Text.AlignVCenter
                }
                background: Rectangle {
                    implicitHeight: 40
                    radius: Theme.t.input.radius
                    color: Theme.t.input.background
                    border.color: temaCombo.activeFocus ? Theme.t.input.borderFocus : Theme.t.input.border
                }
                delegate: ItemDelegate {
                    width: temaCombo.width
                    highlighted: temaCombo.highlightedIndex === index
                    contentItem: Text {
                        text: modelData.nome
                        color: Theme.t.body.color
                        font.family: Theme.t.body.font.family
                        font.pixelSize: Theme.t.body.font.pixelSize
                    }
                    background: Rectangle {
                        color: highlighted ? Theme.t.table.rowHover : Theme.t.surface
                    }
                }
                popup.background: Rectangle {
                    color: Theme.t.surface
                    border.color: Theme.t.border
                    radius: 8
                }
            }

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: preview.implicitHeight + 32
                radius: 8
                color: Theme.t.background
                border.color: Theme.t.border

                ColumnLayout {
                    id: preview
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 10
                    ThemedText { text: "Pré-visualização"; estilo: Theme.t.subtitle }
                    ThemedInput { Layout.fillWidth: true; placeholderText: "Caixa de texto" }
                    ThemedText { text: "23790.12345 60000.000001 23456.789012 1 99990000010000"; estilo: Theme.t.mono }
                    RowLayout {
                        ThemedButton { text: "Primário" }
                        ThemedButton { text: "Secundário"; secundario: true }
                        StatusPill { status: "success" }
                        StatusPill { status: "review" }
                    }
                }
            }

            ThemedButton {
                text: "Fechar"
                Layout.alignment: Qt.AlignRight
                onClicked: configDialog.close()
            }
        }
    }

    // ---------- Layout principal ----------
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 16

        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            ColumnLayout {
                spacing: 2
                ThemedText { text: "Extrator de Boletos"; estilo: Theme.t.title }
                ThemedText {
                    text: viewModel.processando ? viewModel.progresso : viewModel.resumo
                    estilo: Theme.t.subtitle
                }
            }

            Item { Layout.fillWidth: true }

            ThemedButton { text: "＋ Adicionar"; onClicked: abrirDialog.open() }
            ThemedButton {
                text: "Exportar CSV"
                secundario: true
                enabled: viewModel.quantidade > 0 && !viewModel.processando
                onClicked: exportarDialog.open()
            }
            ThemedButton {
                text: "Limpar"
                secundario: true
                enabled: viewModel.quantidade > 0 && !viewModel.processando
                onClicked: { viewModel.limpar(); codigoInput.forceActiveFocus() }
            }
            ThemedButton {
                text: "⚙"
                secundario: true
                implicitWidth: 44
                onClicked: configDialog.open()
            }
        }

        // ---------- Entrada pelo leitor de código de barras ----------
        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            ThemedInput {
                id: codigoInput
                Layout.fillWidth: true
                implicitHeight: 44
                placeholderText: "▮▯▮ Bipe o código de barras ou cole a linha digitável e pressione Enter  (Ctrl+L)"
                font.family: Theme.t.mono.font.family
                font.pixelSize: 15
                maximumLength: 80
                validator: RegularExpressionValidator { regularExpression: /[0-9 .\-]*/ }
                selectByMouse: true

                function enviar() {
                    if (text.trim().length === 0)
                        return
                    if (viewModel.adicionarCodigo(text)) {
                        clear()
                        lista.positionViewAtEnd()
                    } else {
                        selectAll()  // o próximo bipe substitui o texto
                    }
                    forceActiveFocus()
                }

                onAccepted: enviar()
            }

            ThemedButton {
                text: "Inserir"
                implicitHeight: 44
                enabled: codigoInput.text.trim().length > 0
                onClicked: codigoInput.enviar()
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: 10
            color: Theme.t.surface
            border.width: dropArea.containsDrag ? 2 : 1
            border.color: dropArea.containsDrag ? Theme.t.accent : Theme.t.table.border
            clip: true

            DropArea {
                id: dropArea
                anchors.fill: parent
                keys: ["text/uri-list"]
                onDropped: (drop) => viewModel.adicionarArquivos(drop.urls)
            }

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 1
                spacing: 0
                visible: viewModel.quantidade > 0

                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 40
                    color: Theme.t.table.headerBackground
                    radius: 10

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 16
                        anchors.rightMargin: 16
                        spacing: 12
                        Repeater {
                            model: root.colunas
                            Text {
                                text: modelData.t
                                Layout.preferredWidth: modelData.w > 0 ? modelData.w : -1
                                Layout.fillWidth: modelData.w < 0
                                color: Theme.t.table.headerText
                                font.family: Theme.t.table.headerFont.family
                                font.pixelSize: Theme.t.table.headerFont.pixelSize
                                font.weight: Theme.t.table.headerFont.weight
                            }
                        }
                    }
                }

                ListView {
                    id: lista
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    model: viewModel.resultados
                    clip: true
                    ScrollBar.vertical: ScrollBar {}

                    delegate: Rectangle {
                        id: linhaItem
                        required property int index
                        required property string arquivo
                        required property string caminho
                        required property int pagina
                        required property string status
                        required property string tipo
                        required property string emissor
                        required property string vencimento
                        required property string valor
                        required property string linha
                        required property string linhaFormatada
                        required property string mensagem

                        width: lista.width
                        height: 52
                        color: hover.hovered ? Theme.t.table.rowHover
                             : index % 2 ? Theme.t.table.rowAlternate : Theme.t.table.rowBackground

                        HoverHandler { id: hover }

                        ToolTip.visible: hover.hovered
                        ToolTip.delay: 600
                        ToolTip.text: caminho
                            + (tipo ? "\nTipo: " + tipo : "")
                            + (mensagem ? "\n" + mensagem : "")

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 16
                            anchors.rightMargin: 16
                            spacing: 12

                            StatusPill { status: linhaItem.status; Layout.preferredWidth: 92 }
                            ThemedText {
                                Layout.preferredWidth: 170
                                text: linhaItem.arquivo + (linhaItem.pagina > 0 ? "  · p." + linhaItem.pagina : "")
                            }
                            ThemedText { text: linhaItem.emissor || "—"; Layout.preferredWidth: 150 }
                            ThemedText { text: linhaItem.vencimento || "—"; Layout.preferredWidth: 100 }
                            ThemedText {
                                text: linhaItem.valor || "—"
                                Layout.preferredWidth: 110
                                estilo: linhaItem.valor ? Theme.t.mono : Theme.t.body
                            }
                            ThemedText {
                                Layout.fillWidth: true
                                text: linhaItem.linhaFormatada || linhaItem.mensagem
                                estilo: linhaItem.linha ? Theme.t.mono : Theme.t.subtitle
                            }
                            ThemedButton {
                                text: "Copiar"
                                secundario: true
                                Layout.preferredWidth: 90
                                implicitHeight: 32
                                enabled: linhaItem.linha.length > 0
                                onClicked: viewModel.copiar(linhaItem.linha)
                            }
                        }

                        Rectangle {
                            anchors.bottom: parent.bottom
                            width: parent.width
                            height: 1
                            color: Theme.t.table.border
                        }
                    }
                }
            }

            ColumnLayout {
                anchors.centerIn: parent
                visible: viewModel.quantidade === 0
                spacing: 8
                ThemedText {
                    Layout.alignment: Qt.AlignHCenter
                    text: "⬇"
                    font.pixelSize: 48
                    color: Theme.t.accent
                }
                ThemedText {
                    Layout.alignment: Qt.AlignHCenter
                    text: "Arraste PDFs, imagens ou pastas aqui"
                    estilo: Theme.t.title
                }
                ThemedText {
                    Layout.alignment: Qt.AlignHCenter
                    text: "ou clique em ＋ Adicionar, ou bipe o código no campo acima"
                    estilo: Theme.t.subtitle
                }
            }
        }

        ThemedText {
            text: "v" + appVersion
            estilo: Theme.t.subtitle
            Layout.alignment: Qt.AlignRight
        }
    }

    // ---------- Notificação (toast) ----------
    Rectangle {
        id: toast
        property alias texto: toastTexto.text
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 40
        width: toastTexto.implicitWidth + 40
        height: 42
        radius: 21
        color: Theme.t.button.background
        opacity: 0
        visible: opacity > 0
        Behavior on opacity { NumberAnimation { duration: 200 } }

        Text {
            id: toastTexto
            anchors.centerIn: parent
            color: Theme.t.button.text
            font.family: Theme.t.button.font.family
            font.pixelSize: 14
            font.weight: 600
        }

        Timer { id: toastTimer; interval: 2600; onTriggered: toast.opacity = 0 }
    }

    Connections {
        target: viewModel
        function onNotificacao(mensagem) {
            toast.texto = mensagem
            toast.opacity = 1
            toastTimer.restart()
        }
    }
}
