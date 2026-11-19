
import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts

ApplicationWindow {
    visible: true
    width: 1200
    height: 760
    minimumWidth: 900
    minimumHeight: 600

    title: "Extrator de Boletos"

    Material.theme: Material.Dark
    Material.accent: "#38BDF8"

    color: "#101827"

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.preferredWidth: 230
            Layout.fillHeight: true
            color: "#172235"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 24
                spacing: 24

                Label {
                    text: "BOLETO EXTRACTOR"
                    font.pixelSize: 18
                    font.bold: true
                    color: "#38BDF8"
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: "#334155"
                }

                Button {
                    text: "Visão geral"
                    Layout.fillWidth: true
                }

                Button {
                    text: "Nova extração"
                    Layout.fillWidth: true
                }

                Button {
                    text: "Histórico"
                    Layout.fillWidth: true
                }

                Item {
                    Layout.fillHeight: true
                }

                Label {
                    text: "Versão 0.1.0"
                    color: "#94A3B8"
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.margins: 36
            spacing: 24

            Label {
                text: "Extrator de Boletos"
                font.pixelSize: 28
                font.bold: true
                color: "#F8FAFC"
            }

            Label {
                text: "Extraia linhas digitáveis e códigos de barras."
                color: "#94A3B8"
                font.pixelSize: 14
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true

                radius: 16
                color: "#172235"
                border.color: "#334155"
                border.width: 1

                ColumnLayout {
                    anchors.centerIn: parent
                    spacing: 18

                    Label {
                        text: "↑"
                        font.pixelSize: 48
                        color: "#38BDF8"
                        Layout.alignment: Qt.AlignHCenter
                    }

                    Label {
                        text: "Adicione seus boletos"
                        font.pixelSize: 22
                        font.bold: true
                        color: "#F8FAFC"
                        Layout.alignment: Qt.AlignHCenter
                    }

                    Label {
                        text: "Arraste arquivos PDF ou imagens para iniciar."
                        color: "#94A3B8"
                        Layout.alignment: Qt.AlignHCenter
                    }

                    Button {
                        text: "Selecionar arquivos"
                        Layout.alignment: Qt.AlignHCenter
                        highlighted: true
                    }

                    Label {
                        text: "Formatos aceitos: PDF, PNG, JPG e JPEG"
                        color: "#64748B"
                        font.pixelSize: 12
                        Layout.alignment: Qt.AlignHCenter
                    }
                }
            }
        }
    }
}
