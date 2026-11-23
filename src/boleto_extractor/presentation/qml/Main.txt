import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

ApplicationWindow {
    id: root
    width: 1440
    height: 720
    minimumWidth: 1100
    minimumHeight: 500
    visible: true
    title: "Extrator de Boletos"
    color: Theme.t.background

    readonly property var statusTexto: ({
        pending: "Na fila", success: "Sucesso", invalid: "Inválido",
        review: "Revisar", error: "Erro"
    })

    readonly property var colunas: [
        { t: "STATUS", w: 92 }, { t: "ARQUIVO", w: 160 }, { t: "BENEFICIÁRIO", w: 230 },
        { t: "EMISSOR", w: 130 }, { t: "VENCIMENTO", w: 100 }, { t: "VALOR", w: 110 },
        { t: "LINHA DIGITÁVEL", w: -1 }, { t: "", w: 90 }
    ]

    // Mensagens dos testes de conexão
    property string msgBq: ""
    property bool okBq: true
    property bool bqTestando: false
    property string msgDb: ""
    property bool okDb: true

    function mostrarToast(mensagem) {
        toast.texto = mensagem
        toast.opacity = 1
        toastTimer.restart()
    }

    // Aceita CNPJ numérico ou alfanumérico (12 alfanuméricos + 2 dígitos verificadores)
    function testarConsultaCnpj() {
        const cnpj = cnpjTeste.text.toUpperCase().replace(/[^A-Z0-9]/g, "")
        if (!/^[A-Z0-9]{12}\d{2}$/.test(cnpj)) {
            root.okBq = false
            root.msgBq = "Informe um CNPJ válido (14 caracteres, numérico ou alfanumérico)."
            return
        }
        root.bqTestando = true
        root.okBq = true
        root.msgBq = "Consultando…"
        settings.testarConsultaCnpj(cnpj)
    }

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
        selectByMouse: true
        background: Rectangle {
            implicitHeight: 38
            radius: Theme.t.input.radius
            color: Theme.t.input.background
            border.width: campo.activeFocus ? 2 : 1
            border.color: campo.activeFocus ? Theme.t.input.borderFocus : Theme.t.input.border
        }
    }

    component ThemedCheck: CheckBox {
        id: chk
        contentItem: Text {
            text: chk.text
            leftPadding: chk.indicator.width + chk.spacing
            verticalAlignment: Text.AlignVCenter
            color: Theme.t.body.color
            font.family: Theme.t.body.font.family
            font.pixelSize: Theme.t.body.font.pixelSize
        }
    }

    component ThemedTab: TabButton {
        id: aba
        focusPolicy: Qt.NoFocus
        contentItem: Text {
            text: aba.text
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            color: aba.checked ? Theme.t.accent : Theme.t.subtitle.color
            font.family: Theme.t.body.font.family
            font.pixelSize: Theme.t.body.font.pixelSize
            font.weight: aba.checked ? 700 : 400
        }
        background: Rectangle {
            implicitHeight: 38
            color: "transparent"
            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 2
                color: aba.checked ? Theme.t.accent : Theme.t.border
            }
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

    FileDialog {
        id: credencialDialog
        title: "Selecionar chave da conta de serviço (JSON)"
        nameFilters: ["Chave JSON (*.json)"]
        onAccepted: settings.importarCredencial(selectedFile)
    }

    FileDialog {
        id: exportarConfigDialog
        title: "Exportar configuração"
        fileMode: FileDialog.SaveFile
        defaultSuffix: "json"
        nameFilters: ["JSON (*.json)"]
        onAccepted: settings.exportar(selectedFile)
    }

    FileDialog {
        id: importarConfigDialog
        title: "Importar configuração"
        nameFilters: ["JSON (*.json)"]
        onAccepted: settings.importar(selectedFile)
    }

    Connections {
        target: settings
        function onTesteConcluido(tipo, ok, mensagem) {
            if (tipo === "bq") {
                root.msgBq = mensagem
                root.okBq = ok
                // A mensagem inicial "Consultando…" não encerra o teste
                if (!mensagem.startsWith("Consultando"))
                    root.bqTestando = false
            } else {
                root.msgDb = mensagem
                root.okDb = ok
            }
        }
    }

    // ---------- Janela de senha do PDF ----------
    Dialog {
        id: senhaDialog
        modal: true
        anchors.centerIn: parent
        width: 480
        padding: 24
        closePolicy: Popup.NoAutoClose
        property string arquivoAtual: ""

        function enviar() {
            if (senhaInput.text.length === 0)
                return
            viewModel.informarSenha(senhaInput.text, usarProximos.checked, lembrarSenha.checked)
            senhaInput.clear()
            senhaInput.forceActiveFocus()
        }

        onOpened: senhaInput.forceActiveFocus()
        onClosed: codigoInput.forceActiveFocus()

        background: Rectangle {
            color: Theme.t.surface
            radius: 12
            border.color: Theme.t.accent
        }

        ColumnLayout {
            anchors.fill: parent
            spacing: 12

            ThemedText { text: "🔒 PDF protegido por senha"; estilo: Theme.t.title }
            ThemedText { text: viewModel.senhaPosicao; estilo: Theme.t.subtitle }
            ThemedText {
                Layout.fillWidth: true
                text: viewModel.senhaArquivo
                estilo: Theme.t.mono
            }

            ThemedInput {
                id: senhaInput
                Layout.fillWidth: true
                echoMode: TextInput.Password
                placeholderText: "Digite a senha do arquivo e pressione Enter"
                onAccepted: senhaDialog.enviar()
            }

            ThemedText {
                Layout.fillWidth: true
                visible: viewModel.senhaErro.length > 0
                text: viewModel.senhaErro
                color: Theme.t.status.invalid
            }

            ThemedCheck {
                id: usarProximos
                checked: true
                text: "Usar esta senha nos próximos arquivos (só nesta sessão)"
            }
            ThemedCheck {
                id: lembrarSenha
                checked: false
                text: "Lembrar senha (cofre do Windows)"
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                ThemedButton {
                    text: "Pular todos"
                    secundario: true
                    visible: viewModel.senhaRestantes > 1
                    onClicked: viewModel.pularTodasSenhas()
                }
                Item { Layout.fillWidth: true }
                ThemedButton {
                    text: "Pular"
                    secundario: true
                    onClicked: { senhaInput.clear(); viewModel.pularSenha() }
                }
                ThemedButton {
                    text: "Abrir"
                    enabled: senhaInput.text.length > 0
                    onClicked: senhaDialog.enviar()
                }
            }
        }

        Shortcut {
            sequence: "Esc"
            enabled: senhaDialog.opened
            onActivated: { senhaInput.clear(); viewModel.pularSenha() }
        }
    }

    Connections {
        target: viewModel
        function onSenhaChanged() {
            if (viewModel.senhaPendente) {
                if (senhaDialog.arquivoAtual !== viewModel.senhaArquivo) {
                    senhaDialog.arquivoAtual = viewModel.senhaArquivo
                    senhaInput.clear()
                }
                if (!senhaDialog.opened)
                    senhaDialog.open()
            } else {
                senhaDialog.arquivoAtual = ""
                senhaDialog.close()
            }
        }
        function onNotificacao(mensagem) {
            root.mostrarToast(mensagem)
        }
    }

    Dialog {
        id: configDialog
        modal: true
        anchors.centerIn: parent
        width: 600
        height: Math.min(root.height * 0.92, 660)
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

            TabBar {
                id: abas
                Layout.fillWidth: true
                background: Item {}
                ThemedTab { text: "Aparência" }
                ThemedTab { text: "BigQuery (CNPJ)" }
                ThemedTab { text: "MySQL (ERP)" }
            }

            StackLayout {
                currentIndex: abas.currentIndex
                Layout.fillWidth: true
                Layout.fillHeight: true

                // ================= Aparência =================
                ColumnLayout {
                    spacing: 16

                    ThemedText { text: "Tema"; estilo: Theme.t.subtitle }

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

                    Item { Layout.fillHeight: true }
                }

                // ================= BigQuery =================
                ColumnLayout {
                    spacing: 8

                    ThemedCheck {
                        text: "Usar BigQuery como fonte reserva de CNPJ"
                        checked: settings.bqAtivo
                        onToggled: settings.bqAtivo = checked
                    }

                    ThemedText { text: "Credencial (conta de serviço)"; estilo: Theme.t.subtitle }
                    RowLayout {
                        Layout.fillWidth: true
                        ThemedInput {
                            Layout.fillWidth: true
                            readOnly: true
                            text: settings.bqCredencial
                            placeholderText: "Nenhuma credencial importada"
                        }
                        ThemedButton {
                            text: "Importar…"
                            secundario: true
                            onClicked: credencialDialog.open()
                        }
                        ThemedButton {
                            text: "Remover"
                            secundario: true
                            enabled: settings.bqCredencial !== ""
                            onClicked: settings.removerCredencial()
                        }
                    }

                    ThemedText { text: "Projeto (faturamento)"; estilo: Theme.t.subtitle }
                    ThemedInput {
                        Layout.fillWidth: true
                        text: settings.bqProjeto
                        onTextChanged: settings.bqProjeto = text
                    }

                    ThemedText { text: "Tabela"; estilo: Theme.t.subtitle }
                    ThemedInput {
                        Layout.fillWidth: true
                        text: settings.bqTabela
                        placeholderText: "opencnpj-bigquery.public.receita"
                        font.family: Theme.t.mono.font.family
                        onTextChanged: settings.bqTabela = text
                    }

                    ThemedText { text: "Limite por consulta (GB)"; estilo: Theme.t.subtitle }
                    ThemedInput {
                        Layout.preferredWidth: 120
                        text: settings.bqLimiteGb
                        validator: IntValidator { bottom: 1; top: 100 }
                        onTextChanged: if (acceptableInput) settings.bqLimiteGb = parseInt(text)
                    }

                    ThemedText { text: "Testes"; estilo: Theme.t.subtitle }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        ThemedButton {
                            text: "Testar conexão"
                            secundario: true
                            enabled: !root.bqTestando
                            onClicked: {
                                root.bqTestando = true
                                root.okBq = true
                                root.msgBq = "Testando…"
                                settings.testarBigQuery()
                            }
                        }

                        ThemedInput {
                            id: cnpjTeste
                            Layout.fillWidth: true
                            text: "00000000000191"   // Banco do Brasil
                            placeholderText: "CNPJ (numérico ou alfanumérico)"
                            font.family: Theme.t.mono.font.family
                            font.capitalization: Font.AllUppercase
                            maximumLength: 18
                            validator: RegularExpressionValidator { regularExpression: /[0-9A-Za-z.\/-]{0,18}/ }
                            onAccepted: if (!root.bqTestando && settings.bqCredencial !== "") root.testarConsultaCnpj()
                        }

                        ThemedButton {
                            text: root.bqTestando ? "Aguarde…" : "Testar consulta"
                            enabled: !root.bqTestando && settings.bqCredencial !== ""
                            onClicked: root.testarConsultaCnpj()
                        }
                    }

                    ThemedText {
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        elide: Text.ElideNone
                        text: root.msgBq
                        color: root.okBq ? Theme.t.status.success : Theme.t.status.error
                    }

                    Item { Layout.fillHeight: true }
                }

                // ================= MySQL =================
                ColumnLayout {
                    spacing: 8

                    ThemedCheck {
                        text: "Integrar com o banco MySQL do ERP"
                        checked: settings.dbAtivo
                        onToggled: settings.dbAtivo = checked
                    }

                    GridLayout {
                        columns: 2
                        Layout.fillWidth: true
                        columnSpacing: 12
                        rowSpacing: 8

                        ThemedText { text: "Host" }
                        ThemedInput {
                            Layout.fillWidth: true
                            text: settings.dbHost
                            onTextChanged: settings.dbHost = text
                        }

                        ThemedText { text: "Porta" }
                        ThemedInput {
                            Layout.preferredWidth: 120
                            text: settings.dbPorta
                            validator: IntValidator { bottom: 1; top: 65535 }
                            onTextChanged: if (acceptableInput) settings.dbPorta = parseInt(text)
                        }

                        ThemedText { text: "Banco" }
                        ThemedInput {
                            Layout.fillWidth: true
                            text: settings.dbBanco
                            onTextChanged: settings.dbBanco = text
                        }

                        ThemedText { text: "Usuário" }
                        ThemedInput {
                            Layout.fillWidth: true
                            text: settings.dbUsuario
                            onTextChanged: settings.dbUsuario = text
                        }

                        ThemedText { text: "Senha" }
                        ThemedInput {
                            Layout.fillWidth: true
                            echoMode: TextInput.Password
                            placeholderText: settings.dbSenhaSalva ? "•••• (salva no cofre do Windows)" : ""
                            onTextChanged: settings.dbSenha = text
                        }
                    }

                    ThemedCheck {
                        text: "Usar SSL"
                        checked: settings.dbSsl
                        onToggled: settings.dbSsl = checked
                    }

                    RowLayout {
                        spacing: 8
                        ThemedButton {
                            text: "Testar conexão"
                            onClicked: { root.okDb = true; root.msgDb = "Testando…"; settings.testarMySQL() }
                        }
                        ThemedButton { text: "Exportar…"; secundario: true; onClicked: exportarConfigDialog.open() }
                        ThemedButton { text: "Importar…"; secundario: true; onClicked: importarConfigDialog.open() }
                    }
                    ThemedText {
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        elide: Text.ElideNone
                        text: root.msgDb
                        color: root.okDb ? Theme.t.status.success : Theme.t.status.error
                    }

                    Item { Layout.fillHeight: true }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                ThemedButton {
                    text: "Fechar"
                    secundario: true
                    onClicked: configDialog.close()
                }
                ThemedButton {
                    text: "Salvar"
                    onClicked: {
                        if (settings.salvar()) {
                            configDialog.close()
                            root.mostrarToast("Configurações salvas")
                        }
                    }
                }
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
                        required property string beneficiario
                        required property string beneficiarioDoc
                        required property string situacao
                        required property string beneficiarioDetalhe
                        required property bool protegido

                        readonly property bool situacaoAlerta:
                            situacao.length > 0 && situacao.toUpperCase() !== "ATIVA"

                        width: lista.width
                        height: 56
                        color: hover.hovered ? Theme.t.table.rowHover
                             : index % 2 ? Theme.t.table.rowAlternate : Theme.t.table.rowBackground

                        HoverHandler { id: hover }

                        ToolTip.visible: hover.hovered
                        ToolTip.delay: 600
                        ToolTip.text: caminho
                            + (tipo ? "\nTipo: " + tipo : "")
                            + (beneficiarioDetalhe ? "\n\n" + beneficiarioDetalhe : "")
                            + (mensagem ? "\n\n" + mensagem : "")

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 16
                            anchors.rightMargin: 16
                            spacing: 12

                            StatusPill { status: linhaItem.status; Layout.preferredWidth: 92 }
                            ThemedText {
                                Layout.preferredWidth: 160
                                text: (linhaItem.protegido ? "🔒 " : "") + linhaItem.arquivo
                                    + (linhaItem.pagina > 0 ? "  · p." + linhaItem.pagina : "")
                            }

                            ColumnLayout {
                                Layout.preferredWidth: 230
                                Layout.maximumWidth: 230
                                spacing: 1
                                ThemedText {
                                    Layout.fillWidth: true
                                    text: linhaItem.beneficiario || linhaItem.beneficiarioDoc || "—"
                                    estilo: linhaItem.beneficiario ? Theme.t.body
                                          : linhaItem.beneficiarioDoc ? Theme.t.mono : Theme.t.body
                                }
                                ThemedText {
                                    Layout.fillWidth: true
                                    visible: linhaItem.beneficiario.length > 0
                                    estilo: Theme.t.subtitle
                                    font.pixelSize: 11
                                    text: linhaItem.beneficiarioDoc
                                        + (linhaItem.situacao ? "  · " + linhaItem.situacao : "")
                                    color: linhaItem.situacaoAlerta ? Theme.t.status.review
                                                                    : Theme.t.subtitle.color
                                }
                            }

                            ThemedText { text: linhaItem.emissor || "—"; Layout.preferredWidth: 130 }
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
                                text: linhaItem.protegido ? "🔒 Senha" : "Copiar"
                                secundario: !linhaItem.protegido
                                Layout.preferredWidth: 90
                                implicitHeight: 32
                                enabled: linhaItem.protegido || linhaItem.linha.length > 0
                                onClicked: linhaItem.protegido
                                    ? viewModel.informarSenhaLinha(linhaItem.index)
                                    : viewModel.copiar(linhaItem.linha)
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
        z: 200
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
}
