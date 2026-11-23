import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

Dialog {
    id: root
    title: "Configurações"
    modal: true
    anchors.centerIn: parent
    width: Math.min(parent ? parent.width * 0.9 : 640, 640)
    height: Math.min(parent ? parent.height * 0.9 : 620, 620)
    standardButtons: Dialog.Cancel | Dialog.Save

    property string msgBq: ""
    property bool okBq: true
    property string msgDb: ""
    property bool okDb: true

    onAccepted: {
        if (!settings.salvar())
            root.open()
    }

    Connections {
        target: settings
        function onTesteConcluido(tipo, ok, mensagem) {
            if (tipo === "bq") { root.msgBq = mensagem; root.okBq = ok }
            else               { root.msgDb = mensagem; root.okDb = ok }
        }
    }

    FileDialog {
        id: dlgCredencial
        title: "Selecionar chave da conta de serviço (JSON)"
        nameFilters: ["Chave JSON (*.json)"]
        onAccepted: settings.importarCredencial(selectedFile)
    }
    FileDialog {
        id: dlgExportar
        title: "Exportar configuração"
        fileMode: FileDialog.SaveFile
        nameFilters: ["JSON (*.json)"]
        onAccepted: settings.exportar(selectedFile)
    }
    FileDialog {
        id: dlgImportar
        title: "Importar configuração"
        nameFilters: ["JSON (*.json)"]
        onAccepted: settings.importar(selectedFile)
    }

    contentItem: ColumnLayout {
        spacing: 8

        TabBar {
            id: abas
            Layout.fillWidth: true
            TabButton { text: "BigQuery (CNPJ)" }
            TabButton { text: "MySQL (ERP)" }
        }

        StackLayout {
            currentIndex: abas.currentIndex
            Layout.fillWidth: true
            Layout.fillHeight: true

            // ------------------------------------------------ BigQuery
            ScrollView {
                clip: true
                ColumnLayout {
                    width: parent.width
                    spacing: 8

                    CheckBox {
                        text: "Usar BigQuery como fonte reserva de CNPJ"
                        checked: settings.bqAtivo
                        onToggled: settings.bqAtivo = checked
                    }

                    Label { text: "Credencial (conta de serviço)" }
                    RowLayout {
                        Layout.fillWidth: true
                        TextField {
                            Layout.fillWidth: true
                            readOnly: true
                            text: settings.bqCredencial
                            placeholderText: "Nenhuma credencial importada"
                        }
                        Button { text: "Importar…"; onClicked: dlgCredencial.open() }
                        Button {
                            text: "Remover"
                            enabled: settings.bqCredencial !== ""
                            onClicked: settings.removerCredencial()
                        }
                    }

                    Label { text: "Projeto (faturamento)" }
                    TextField {
                        Layout.fillWidth: true
                        text: settings.bqProjeto
                        onEditingFinished: settings.bqProjeto = text
                    }

                    Label { text: "Tabela" }
                    TextField {
                        Layout.fillWidth: true
                        text: settings.bqTabela
                        onEditingFinished: settings.bqTabela = text
                    }

                    Label { text: "Limite por consulta (GB)" }
                    SpinBox {
                        from: 1; to: 100
                        value: settings.bqLimiteGb
                        onValueModified: settings.bqLimiteGb = value
                    }

                    Button { text: "Testar conexão"; onClicked: { root.msgBq = "Testando…"; settings.testarBigQuery() } }
                    Label {
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        text: root.msgBq
                        color: root.okBq ? "#2e7d32" : "#c62828"
                    }
                }
            }

            // ------------------------------------------------ MySQL
            ScrollView {
                clip: true
                ColumnLayout {
                    width: parent.width
                    spacing: 8

                    CheckBox {
                        text: "Integrar com o banco MySQL do ERP"
                        checked: settings.dbAtivo
                        onToggled: settings.dbAtivo = checked
                    }

                    GridLayout {
                        columns: 2
                        Layout.fillWidth: true
                        columnSpacing: 8

                        Label { text: "Host" }
                        TextField {
                            Layout.fillWidth: true
                            text: settings.dbHost
                            onEditingFinished: settings.dbHost = text
                        }

                        Label { text: "Porta" }
                        SpinBox {
                            from: 1; to: 65535
                            editable: true
                            value: settings.dbPorta
                            onValueModified: settings.dbPorta = value
                        }

                        Label { text: "Banco" }
                        TextField {
                            Layout.fillWidth: true
                            text: settings.dbBanco
                            onEditingFinished: settings.dbBanco = text
                        }

                        Label { text: "Usuário" }
                        TextField {
                            Layout.fillWidth: true
                            text: settings.dbUsuario
                            onEditingFinished: settings.dbUsuario = text
                        }

                        Label { text: "Senha" }
                        TextField {
                            Layout.fillWidth: true
                            echoMode: TextInput.Password
                            placeholderText: settings.dbSenhaSalva ? "•••• (salva no cofre do Windows)" : ""
                            onEditingFinished: settings.dbSenha = text
                        }
                    }

                    CheckBox {
                        text: "Usar SSL"
                        checked: settings.dbSsl
                        onToggled: settings.dbSsl = checked
                    }

                    RowLayout {
                        Button { text: "Testar conexão"; onClicked: { root.msgDb = "Testando…"; settings.testarMySQL() } }
                        Button { text: "Exportar…"; onClicked: dlgExportar.open() }
                        Button { text: "Importar…"; onClicked: dlgImportar.open() }
                    }
                    Label {
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        text: root.msgDb
                        color: root.okDb ? "#2e7d32" : "#c62828"
                    }
                }
            }
        }
    }
}
