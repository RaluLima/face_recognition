import sys, os, json, datetime, subprocess
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton,
    QListWidget, QFileDialog, QMessageBox, QHBoxLayout, QTextEdit, QStackedWidget,
    QInputDialog, QListWidgetItem, QDialog, QDialogButtonBox, QFrame
)
from PyQt5.QtCore import Qt, QTimer

# Novos imports para reconhecimento facial
import cv2
import face_recognition
import numpy as np

# Caminhos dos arquivos
BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
USERS_FILE = os.path.join(DATA_DIR, "usuarios.json")
LOG_FILE = os.path.join(DATA_DIR, "logs.txt")
PASTAS_FILE = os.path.join(DATA_DIR, "pastas.json")
SESSOES_FILE = os.path.join(DATA_DIR, "sessoes.json")
COFRES_DIR = os.path.join(DATA_DIR, "cofres")

# Garante pastas e arquivos
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(COFRES_DIR, exist_ok=True)
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump({}, f)
if not os.path.exists(PASTAS_FILE):
    with open(PASTAS_FILE, "w", encoding="utf-8") as f:
        json.dump([], f)
if not os.path.exists(SESSOES_FILE):
    with open(SESSOES_FILE, "w", encoding="utf-8") as f:
        json.dump({}, f)

# ------------------------- Funções auxiliares -------------------------
def salvar_log(msg):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] {msg}\n")

def carregar_usuarios():
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def salvar_usuarios(data):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def carregar_pastas():
    try:
        with open(PASTAS_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return []
            return json.loads(content)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def salvar_pastas(lista):
    with open(PASTAS_FILE, "w", encoding="utf-8") as f:
        json.dump(lista, f, indent=4, ensure_ascii=False)

# ------------------------- Funções de Sessão -------------------------
def carregar_sessoes():
    try:
        with open(SESSOES_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def salvar_sessoes(data):
    with open(SESSOES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def criar_sessao(usuario):
    import uuid
    sessoes = carregar_sessoes()
    sessao_id = str(uuid.uuid4())
    agora = datetime.datetime.now()
    expira = agora + datetime.timedelta(minutes=15)
    sessoes[sessao_id] = {
        "usuario": usuario,
        "autenticado_em": agora.strftime('%Y-%m-%d %H:%M:%S'),
        "expira_em": expira.strftime('%Y-%m-%d %H:%M:%S'),
        "metodo": "facial"
    }
    salvar_sessoes(sessoes)
    salvar_log(f"Sessão criada para '{usuario}' (ID: {sessao_id}, expira em 15min)")
    return sessao_id

def validar_sessao(sessao_id):
    if not sessao_id:
        return None
    sessoes = carregar_sessoes()
    if sessao_id not in sessoes:
        return None
    sessao = sessoes[sessao_id]
    expira = datetime.datetime.strptime(sessao["expira_em"], '%Y-%m-%d %H:%M:%S')
    if datetime.datetime.now() > expira:
        del sessoes[sessao_id]
        salvar_sessoes(sessoes)
        salvar_log(f"Sessão {sessao_id} expirou")
        return None
    return sessao["usuario"]

def encerrar_sessao(sessao_id):
    if not sessao_id:
        return
    sessoes = carregar_sessoes()
    if sessao_id in sessoes:
        usuario = sessoes[sessao_id]["usuario"]
        del sessoes[sessao_id]
        salvar_sessoes(sessoes)
        salvar_log(f"Sessão encerrada para '{usuario}' (ID: {sessao_id})")

# ------------------------- Funções de Cofre -------------------------
def obter_cofre_usuario(usuario):
    cofre_path = os.path.join(COFRES_DIR, usuario)
    os.makedirs(cofre_path, exist_ok=True)
    return cofre_path

def obter_metadata_cofre(usuario):
    metadata_file = os.path.join(obter_cofre_usuario(usuario), "metadata.json")
    if not os.path.exists(metadata_file):
        return {"arquivos": []}
    try:
        with open(metadata_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"arquivos": []}

def salvar_metadata_cofre(usuario, metadata):
    metadata_file = os.path.join(obter_cofre_usuario(usuario), "metadata.json")
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4, ensure_ascii=False)

# ------------------------- Tela de Gerenciamento de Usuários -------------------------
class GerenciarUsuarios(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.setStyleSheet("background-color: #f0f4f7;")

        self.label = QLabel("👤 Gerenciar Usuários")
        self.label.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px; color: #333;")
        layout.addWidget(self.label)

        self.lista_usuarios = QListWidget()
        layout.addWidget(self.lista_usuarios)

        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("Cadastrar Usuário")
        self.btn_add.setStyleSheet(self.botao_style())
        self.btn_remover = QPushButton("Remover Usuário")
        self.btn_remover.setStyleSheet(self.botao_style())
        self.btn_pastas = QPushButton("Definir Pastas do Usuário")
        self.btn_pastas.setStyleSheet(self.botao_style())
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_remover)
        btn_layout.addWidget(self.btn_pastas)
        layout.addLayout(btn_layout)

        # Segunda linha de botões
        btn_layout2 = QHBoxLayout()
        self.btn_cadastrar_face = QPushButton("📸 Cadastrar/Atualizar Face")
        self.btn_cadastrar_face.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 6px;
                padding: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3e8e41;
            }
        """)
        btn_layout2.addWidget(self.btn_cadastrar_face)
        layout.addLayout(btn_layout2)

        self.setLayout(layout)
        self.carregar_lista()

        self.btn_add.clicked.connect(self.cadastrar_usuario)
        self.btn_remover.clicked.connect(self.remover_usuario)
        self.btn_pastas.clicked.connect(self.definir_pastas)
        self.btn_cadastrar_face.clicked.connect(self.atualizar_face_usuario)

    def botao_style(self):
        return """
            QPushButton {
                background-color: #0078d7;
                color: white;
                border-radius: 6px;
                padding: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #005fa3;
            }
        """

    def carregar_lista(self):
        self.lista_usuarios.clear()
        for nome in carregar_usuarios().keys():
            self.lista_usuarios.addItem(nome)

    def cadastrar_usuario(self):
        nome, ok = QInputDialog.getText(self, "Cadastrar Usuário", "Nome do usuário:")
        if not ok or not nome.strip():
            return
        nome = nome.strip()
        usuarios = carregar_usuarios()
        if nome in usuarios:
            QMessageBox.warning(self, "Erro", "Usuário já existe!")
            return

        # Pergunta se deseja cadastrar reconhecimento facial
        reply = QMessageBox.question(self, "Reconhecimento Facial",
                                     f"Deseja cadastrar reconhecimento facial para '{nome}'?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)

        embedding = None
        if reply == QMessageBox.Yes:
            embedding = self.capturar_face_usuario(nome)
            if embedding is None:
                cancelar = QMessageBox.question(self, "Cadastro Incompleto",
                                               "Falha ao capturar face. Deseja criar usuário sem reconhecimento facial?",
                                               QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if cancelar == QMessageBox.No:
                    return

        usuarios[nome] = {
            "pastas": [],
            "embedding": embedding.tolist() if embedding is not None else None
        }
        salvar_usuarios(usuarios)
        msg_embedding = "com reconhecimento facial" if embedding is not None else "sem reconhecimento facial"
        salvar_log(f"Usuário '{nome}' cadastrado {msg_embedding}.")
        QMessageBox.information(self, "Sucesso", f"Usuário cadastrado {msg_embedding}!")
        self.carregar_lista()

    def capturar_face_usuario(self, nome):
        """Captura a face do usuário usando webcam e retorna o embedding facial"""
        video = None
        try:
            # Tenta abrir a câmera
            try:
                video = cv2.VideoCapture(0)
            except Exception as e:
                QMessageBox.critical(self, "Erro ao Acessar Câmera",
                                   f"Não foi possível inicializar a câmera.\n\n"
                                   f"Erro: {str(e)}\n\n"
                                   f"Verifique se:\n"
                                   f"• A câmera está conectada\n"
                                   f"• Nenhum outro programa está usando a câmera\n"
                                   f"• Você tem permissão para acessar a câmera")
                return None

            if not video.isOpened():
                QMessageBox.critical(self, "Erro ao Acessar Câmera",
                                   "Não foi possível abrir a câmera!\n\n"
                                   "Possíveis causas:\n"
                                   "• Câmera está sendo usada por outro programa\n"
                                   "• Câmera não está conectada\n"
                                   "•Driver da câmera não está instalado\n"
                                   "• Permissões de acesso à câmera negadas")
                return None

            QMessageBox.information(self, "Captura Facial",
                                   f"📸 Cadastro facial de '{nome}'\n\n"
                                   "Instruções:\n"
                                   "• Posicione seu rosto no centro da tela\n"
                                   "• Aguarde o rosto ser detectado (retângulo verde)\n"
                                   "• Pressione ESPAÇO para capturar\n"
                                   "• Pressione Q para cancelar")

            embedding_capturado = None
            font = cv2.FONT_HERSHEY_SIMPLEX
            frame_count = 0
            max_failed_frames = 30  # Máximo de frames consecutivos sem captura

            while True:
                try:
                    ret, frame = video.read()
                    if not ret:
                        frame_count += 1
                        if frame_count > max_failed_frames:
                            raise Exception("Falha ao capturar frames da câmera. A câmera pode ter sido desconectada.")
                        continue

                    frame_count = 0  # Reset contador se frame for capturado com sucesso

                    # Redimensiona para processar mais rápido
                    small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
                    rgb = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

                    # Detecta rostos e gera embeddings
                    try:
                        faces = face_recognition.face_locations(rgb)
                        embeddings = face_recognition.face_encodings(rgb, faces)
                    except Exception as e:
                        # Erro no reconhecimento facial
                        raise Exception(f"Erro no processamento de reconhecimento facial: {str(e)}")

                    # Frame para exibição (tamanho original)
                    display_frame = frame.copy()

                    # Determina status
                    if len(faces) == 0:
                        status_msg = "Nenhum rosto detectado"
                        color = (0, 0, 255)  # Vermelho
                    elif len(faces) > 1:
                        status_msg = "Multiplos rostos - apenas 1 permitido"
                        color = (0, 165, 255)  # Laranja
                    else:
                        status_msg = "Rosto detectado - Pressione ESPACO"
                        color = (0, 255, 0)  # Verde

                        # Desenha retângulo ao redor do rosto (escala 2x pois redimensionamos)
                        for (top, right, bottom, left) in faces:
                            top *= 2
                            right *= 2
                            bottom *= 2
                            left *= 2
                            cv2.rectangle(display_frame, (left, top), (right, bottom), color, 3)

                    # Adiciona texto de status
                    cv2.putText(display_frame, status_msg, (10, 30), font, 0.9, color, 2)
                    cv2.putText(display_frame, f"Usuario: {nome}", (10, 70), font, 0.7, (255, 255, 255), 2)
                    cv2.putText(display_frame, "Q = Cancelar", (10, display_frame.shape[0] - 10), font, 0.6, (255, 255, 255), 1)

                    try:
                        cv2.imshow("Cadastro Facial", display_frame)
                    except Exception as e:
                        raise Exception(f"Erro ao exibir janela de vídeo: {str(e)}")

                    key = cv2.waitKey(1) & 0xFF

                    # Captura com ESPAÇO se houver exatamente 1 rosto
                    if key == ord(' ') and len(faces) == 1:
                        embedding_capturado = embeddings[0]
                        # Feedback visual
                        cv2.putText(display_frame, "CAPTURADO!", (display_frame.shape[1]//2 - 100, display_frame.shape[0]//2),
                                   font, 1.5, (0, 255, 0), 3)
                        cv2.imshow("Cadastro Facial", display_frame)
                        cv2.waitKey(1000)  # Mostra por 1 segundo
                        break
                    elif key == ord('q'):
                        break

                except Exception as e:
                    # Erro durante o loop de captura
                    if video is not None:
                        video.release()
                    cv2.destroyAllWindows()
                    QMessageBox.critical(self, "Erro Durante Captura",
                                       f"Ocorreu um erro durante a captura:\n\n{str(e)}")
                    return None

            # Libera recursos
            if video is not None:
                video.release()
            cv2.destroyAllWindows()

            if embedding_capturado is not None:
                QMessageBox.information(self, "Sucesso", f"✅ Face de '{nome}' capturada com sucesso!")
                return embedding_capturado
            else:
                return None

        except Exception as e:
            # Erro geral não capturado
            QMessageBox.critical(self, "Erro Inesperado",
                               f"Ocorreu um erro inesperado ao capturar face:\n\n"
                               f"Erro: {str(e)}\n\n"
                               f"Tipo: {type(e).__name__}")
            try:
                if video is not None:
                    video.release()
                cv2.destroyAllWindows()
            except:
                pass
            return None

    def atualizar_face_usuario(self):
        """Cadastra ou atualiza a face de um usuário existente"""
        item = self.lista_usuarios.currentItem()
        if not item:
            QMessageBox.warning(self, "Erro", "Selecione um usuário para cadastrar/atualizar a face.")
            return

        nome = item.text()
        usuarios = carregar_usuarios()
        if nome not in usuarios:
            QMessageBox.warning(self, "Erro", "Usuário não encontrado!")
            return

        # Verifica se já tem face cadastrada
        tem_face = usuarios[nome].get("embedding") is not None
        if tem_face:
            msg = f"O usuário '{nome}' já possui face cadastrada.\nDeseja atualizar?"
        else:
            msg = f"Cadastrar reconhecimento facial para '{nome}'?"

        reply = QMessageBox.question(self, "Reconhecimento Facial", msg,
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if reply == QMessageBox.No:
            return

        # Captura a face
        embedding = self.capturar_face_usuario(nome)
        if embedding is None:
            QMessageBox.warning(self, "Falha", "Não foi possível capturar a face.")
            return

        # Atualiza no JSON
        usuarios[nome]["embedding"] = embedding.tolist()
        salvar_usuarios(usuarios)

        acao = "atualizada" if tem_face else "cadastrada"
        salvar_log(f"Face do usuário '{nome}' {acao}.")
        QMessageBox.information(self, "Sucesso", f"✅ Face {acao} com sucesso para '{nome}'!")

    def remover_usuario(self):
        item = self.lista_usuarios.currentItem()
        if not item:
            QMessageBox.warning(self, "Erro", "Selecione um usuário.")
            return
        nome = item.text()
        usuarios = carregar_usuarios()
        if nome in usuarios:
            reply = QMessageBox.question(self, "Confirmar remoção", f"Remover o usuário '{nome}'?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                del usuarios[nome]
                salvar_usuarios(usuarios)
                salvar_log(f"Usuário '{nome}' removido.")
                QMessageBox.information(self, "Removido", "Usuário removido com sucesso.")
                self.carregar_lista()

    def definir_pastas(self):
        item = self.lista_usuarios.currentItem()
        if not item:
            QMessageBox.warning(self, "Erro", "Selecione um usuário.")
            return

        nome = item.text()
        usuarios = carregar_usuarios()
        if nome not in usuarios:
            QMessageBox.warning(self, "Erro", "Usuário não existe nos dados.")
            return

        pastas_disponiveis = carregar_pastas()
        if not pastas_disponiveis:
            QMessageBox.warning(self, "Erro", "Nenhuma pasta registrada. Cadastre em 'Gerenciar Pastas'.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Definir Pastas para: " + nome)
        dlg.resize(500, 400)
        dlg_layout = QVBoxLayout(dlg)
        info = QLabel("Selecione as pastas que deseja dar acesso (Ctrl+Clique para múltiplas):")
        dlg_layout.addWidget(info)

        list_widget = QListWidget()
        list_widget.setSelectionMode(QListWidget.MultiSelection)
        user_pastas = usuarios[nome].get("pastas", [])
        for pasta in pastas_disponiveis:
            itm = QListWidgetItem(pasta)
            list_widget.addItem(itm)
            if pasta in user_pastas:
                itm.setSelected(True)
        dlg_layout.addWidget(list_widget)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        dlg_layout.addWidget(buttons)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)

        if dlg.exec_() == QDialog.Accepted:
            selecionadas = [i.text() for i in list_widget.selectedItems()]
            usuarios[nome]["pastas"] = selecionadas
            salvar_usuarios(usuarios)
            salvar_log(f"Usuário '{nome}' teve acesso atualizado: {', '.join(selecionadas) if selecionadas else '(nenhuma)'}")
            QMessageBox.information(self, "Atualizado", "Acesso atualizado com sucesso.")

# ------------------------- Tela de Gerenciamento de Pastas -------------------------
class GerenciarPastas(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.setStyleSheet("background-color: #f0f4f7;")

        self.label = QLabel("📁 Gerenciar Pastas Disponíveis")
        self.label.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px; color: #333;")
        layout.addWidget(self.label)

        self.lista_pastas = QListWidget()
        layout.addWidget(self.lista_pastas)

        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("Adicionar Pasta")
        self.btn_remover = QPushButton("Remover Pasta")
        self.btn_add.setStyleSheet(GerenciarUsuarios.botao_style(self))
        self.btn_remover.setStyleSheet(GerenciarUsuarios.botao_style(self))
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_remover)
        layout.addLayout(btn_layout)

        self.setLayout(layout)
        self.refresh_pastas()
        self.btn_add.clicked.connect(self.adicionar_pasta)
        self.btn_remover.clicked.connect(self.remover_pasta)

    def refresh_pastas(self):
        self.lista_pastas.clear()
        for p in carregar_pastas():
            self.lista_pastas.addItem(p)

    def adicionar_pasta(self):
        pasta = QFileDialog.getExistingDirectory(self, "Selecione uma pasta")
        if not pasta:
            return
        pastas = carregar_pastas()
        if pasta in pastas:
            QMessageBox.warning(self, "Aviso", "Esta pasta já está cadastrada.")
            return
        pastas.append(pasta)
        salvar_pastas(pastas)
        salvar_log(f"Pasta adicionada: {pasta}")
        self.refresh_pastas()

    def remover_pasta(self):
        item = self.lista_pastas.currentItem()
        if not item:
            QMessageBox.warning(self, "Erro", "Selecione uma pasta.")
            return
        pasta = item.text()
        pastas = carregar_pastas()
        if pasta in pastas:
            reply = QMessageBox.question(self, "Confirmar", f"Remover a pasta:\n{pasta} ?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                pastas.remove(pasta)
                salvar_pastas(pastas)
                salvar_log(f"Pasta removida: {pasta}")
                usuarios = carregar_usuarios()
                changed = False
                for u, info in usuarios.items():
                    if "pastas" in info and pasta in info["pastas"]:
                        info["pastas"] = [p for p in info["pastas"] if p != pasta]
                        changed = True
                        salvar_log(f"Removida referência da pasta '{pasta}' do usuário '{u}'")
                if changed:
                    salvar_usuarios(usuarios)
                self.refresh_pastas()

# ------------------------- Logs em Tempo Real -------------------------
class LogsTempoReal(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.setStyleSheet("background-color: #f0f4f7;")
        self.label = QLabel("🧾 Logs do Sistema (tempo real)")
        self.label.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px; color: #333;")
        layout.addWidget(self.label)

        self.texto_log = QTextEdit()
        self.texto_log.setReadOnly(True)
        layout.addWidget(self.texto_log)
        self.setLayout(layout)

        self.atualizar_logs()
        self.timer = QTimer()
        self.timer.timeout.connect(self.atualizar_logs)
        self.timer.start(1000)

    def atualizar_logs(self):
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                conteudo = f.read()
            self.texto_log.setPlainText(conteudo)
            self.texto_log.moveCursor(self.texto_log.textCursor().End)

# ------------------------- Painel do Administrador -------------------------
class AdminPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Painel do Administrador")
        self.resize(850, 500)

        layout = QHBoxLayout()
        self.menu = QVBoxLayout()
        self.stack = QStackedWidget()

        self.btn_usuarios = QPushButton("Gerenciar Usuários")
        self.btn_pastas = QPushButton("Gerenciar Pastas")
        self.btn_logs = QPushButton("Ver Logs em Tempo Real")

        for btn in [self.btn_usuarios, self.btn_pastas, self.btn_logs]:
            btn.setStyleSheet("""
                QPushButton {
                    padding:10px; font-size:15px; text-align:left; background-color:#0078d7; color:white; border-radius:6px;
                }
                QPushButton:hover {
                    background-color:#005fa3;
                }
            """)
            self.menu.addWidget(btn)
        self.menu.addStretch()

        self.tela_usuarios = GerenciarUsuarios()
        self.tela_pastas = GerenciarPastas()
        self.tela_logs = LogsTempoReal()

        self.stack.addWidget(self.tela_usuarios)
        self.stack.addWidget(self.tela_pastas)
        self.stack.addWidget(self.tela_logs)

        layout.addLayout(self.menu, 1)
        layout.addWidget(self.stack, 4)
        self.setLayout(layout)

        self.btn_usuarios.clicked.connect(lambda: self.stack.setCurrentWidget(self.tela_usuarios))
        self.btn_pastas.clicked.connect(lambda: self.stack.setCurrentWidget(self.tela_pastas))
        self.btn_logs.clicked.connect(lambda: self.stack.setCurrentWidget(self.tela_logs))

# ------------------------- Tela do Cofre -------------------------
class CofrePanel(QWidget):
    def __init__(self, usuario, sessao_id):
        super().__init__()
        self.usuario = usuario
        self.sessao_id = sessao_id
        self.setWindowTitle(f"Cofre Digital - {usuario}")
        self.resize(700, 500)

        layout = QVBoxLayout()
        layout.setSpacing(10)

        # Cabeçalho
        header = QLabel(f"🔒 Cofre Digital de {usuario}")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #333; padding: 10px;")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        # Informações da sessão
        self.label_sessao = QLabel()
        self.label_sessao.setStyleSheet("color: #666; font-size: 11px; padding: 5px;")
        layout.addWidget(self.label_sessao)
        self.atualizar_info_sessao()

        # Área de botões de ação
        btn_layout = QHBoxLayout()
        self.btn_upload = QPushButton("📤 Upload Arquivo")
        self.btn_download = QPushButton("💾 Download")
        self.btn_visualizar = QPushButton("👁️ Visualizar")
        self.btn_excluir = QPushButton("🗑️ Excluir")

        for btn in [self.btn_upload, self.btn_download, self.btn_visualizar, self.btn_excluir]:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #0078d7;
                    color: white;
                    border-radius: 6px;
                    padding: 8px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #005fa3;
                }
            """)

        self.btn_excluir.setStyleSheet("""
            QPushButton {
                background-color: #d32f2f;
                color: white;
                border-radius: 6px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #9a0007;
            }
        """)

        btn_layout.addWidget(self.btn_upload)
        btn_layout.addWidget(self.btn_download)
        btn_layout.addWidget(self.btn_visualizar)
        btn_layout.addWidget(self.btn_excluir)
        layout.addLayout(btn_layout)

        # Lista de arquivos
        self.lista_arquivos = QListWidget()
        self.lista_arquivos.setStyleSheet("font-size: 12px; padding: 5px;")
        layout.addWidget(self.lista_arquivos)

        # Botão sair
        self.btn_sair = QPushButton("🚪 Sair do Cofre")
        self.btn_sair.setStyleSheet("""
            QPushButton {
                background-color: #666;
                color: white;
                border-radius: 6px;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #444;
            }
        """)
        layout.addWidget(self.btn_sair)

        self.setLayout(layout)

        # Conectar eventos
        self.btn_upload.clicked.connect(self.upload_arquivo)
        self.btn_download.clicked.connect(self.download_arquivo)
        self.btn_visualizar.clicked.connect(self.visualizar_arquivo)
        self.btn_excluir.clicked.connect(self.excluir_arquivo)
        self.btn_sair.clicked.connect(self.sair_cofre)

        # Timer para atualizar sessão e verificar timeout
        self.timer = QTimer()
        self.timer.timeout.connect(self.verificar_sessao)
        self.timer.start(5000)  # verifica a cada 5 segundos

        # Carregar arquivos
        self.carregar_arquivos()

    def atualizar_info_sessao(self):
        sessoes = carregar_sessoes()
        if self.sessao_id in sessoes:
            sessao = sessoes[self.sessao_id]
            expira = datetime.datetime.strptime(sessao["expira_em"], '%Y-%m-%d %H:%M:%S')
            agora = datetime.datetime.now()
            tempo_restante = expira - agora
            minutos = int(tempo_restante.total_seconds() / 60)
            segundos = int(tempo_restante.total_seconds() % 60)
            self.label_sessao.setText(f"⏱️ Sessão expira em: {minutos}m {segundos}s")

    def verificar_sessao(self):
        usuario = validar_sessao(self.sessao_id)
        if not usuario:
            QMessageBox.warning(self, "Sessão Expirada", "Sua sessão expirou. Faça login novamente.")
            self.close()
        else:
            self.atualizar_info_sessao()

    def carregar_arquivos(self):
        if not validar_sessao(self.sessao_id):
            QMessageBox.warning(self, "Erro", "Sessão inválida!")
            self.close()
            return

        self.lista_arquivos.clear()
        metadata = obter_metadata_cofre(self.usuario)

        for arq in metadata.get("arquivos", []):
            nome = arq.get("nome", "")
            tamanho_bytes = arq.get("tamanho", 0)
            tamanho_kb = tamanho_bytes / 1024
            data = arq.get("data_upload", "")

            if tamanho_kb < 1024:
                tamanho_str = f"{tamanho_kb:.2f} KB"
            else:
                tamanho_str = f"{tamanho_kb/1024:.2f} MB"

            display = f"{nome} ({tamanho_str}) - {data}"
            self.lista_arquivos.addItem(display)

    def upload_arquivo(self):
        if not validar_sessao(self.sessao_id):
            QMessageBox.warning(self, "Erro", "Sessão inválida!")
            self.close()
            return

        arquivo, _ = QFileDialog.getOpenFileName(self, "Selecione um arquivo para upload")
        if not arquivo:
            return

        nome_arquivo = os.path.basename(arquivo)
        cofre_path = obter_cofre_usuario(self.usuario)
        destino = os.path.join(cofre_path, nome_arquivo)

        # Verifica se já existe
        metadata = obter_metadata_cofre(self.usuario)
        nomes_existentes = [a["nome"] for a in metadata.get("arquivos", [])]
        if nome_arquivo in nomes_existentes:
            reply = QMessageBox.question(self, "Arquivo Existente",
                                         f"O arquivo '{nome_arquivo}' já existe. Sobrescrever?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No:
                return
            # Remove da metadata
            metadata["arquivos"] = [a for a in metadata["arquivos"] if a["nome"] != nome_arquivo]

        # Copia arquivo
        try:
            import shutil
            shutil.copy2(arquivo, destino)

            # Atualiza metadata
            tamanho = os.path.getsize(destino)
            agora = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            metadata["arquivos"].append({
                "nome": nome_arquivo,
                "tamanho": tamanho,
                "data_upload": agora
            })
            salvar_metadata_cofre(self.usuario, metadata)
            salvar_log(f"[COFRE] '{self.usuario}' fez upload de '{nome_arquivo}' ({tamanho} bytes)")

            QMessageBox.information(self, "Sucesso", f"Arquivo '{nome_arquivo}' enviado ao cofre!")
            self.carregar_arquivos()
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao fazer upload:\n{e}")
            salvar_log(f"[COFRE] Erro no upload de '{nome_arquivo}' por '{self.usuario}': {e}")

    def download_arquivo(self):
        if not validar_sessao(self.sessao_id):
            QMessageBox.warning(self, "Erro", "Sessão inválida!")
            self.close()
            return

        item = self.lista_arquivos.currentItem()
        if not item:
            QMessageBox.warning(self, "Erro", "Selecione um arquivo para download.")
            return

        # Extrai nome do arquivo do display
        display = item.text()
        nome_arquivo = display.split(" (")[0]

        cofre_path = obter_cofre_usuario(self.usuario)
        origem = os.path.join(cofre_path, nome_arquivo)

        if not os.path.exists(origem):
            QMessageBox.warning(self, "Erro", "Arquivo não encontrado no cofre!")
            return

        # Escolhe destino
        destino, _ = QFileDialog.getSaveFileName(self, "Salvar arquivo como", nome_arquivo)
        if not destino:
            return

        try:
            import shutil
            shutil.copy2(origem, destino)
            salvar_log(f"[COFRE] '{self.usuario}' fez download de '{nome_arquivo}'")
            QMessageBox.information(self, "Sucesso", f"Arquivo baixado para:\n{destino}")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao fazer download:\n{e}")
            salvar_log(f"[COFRE] Erro no download de '{nome_arquivo}' por '{self.usuario}': {e}")

    def visualizar_arquivo(self):
        if not validar_sessao(self.sessao_id):
            QMessageBox.warning(self, "Erro", "Sessão inválida!")
            self.close()
            return

        item = self.lista_arquivos.currentItem()
        if not item:
            QMessageBox.warning(self, "Erro", "Selecione um arquivo para visualizar.")
            return

        display = item.text()
        nome_arquivo = display.split(" (")[0]

        cofre_path = obter_cofre_usuario(self.usuario)
        arquivo = os.path.join(cofre_path, nome_arquivo)

        if not os.path.exists(arquivo):
            QMessageBox.warning(self, "Erro", "Arquivo não encontrado no cofre!")
            return

        try:
            if sys.platform == 'win32':
                os.startfile(arquivo)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', arquivo])
            else:
                subprocess.Popen(['xdg-open', arquivo])
            salvar_log(f"[COFRE] '{self.usuario}' visualizou '{nome_arquivo}'")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao abrir arquivo:\n{e}")
            salvar_log(f"[COFRE] Erro ao visualizar '{nome_arquivo}' por '{self.usuario}': {e}")

    def excluir_arquivo(self):
        if not validar_sessao(self.sessao_id):
            QMessageBox.warning(self, "Erro", "Sessão inválida!")
            self.close()
            return

        item = self.lista_arquivos.currentItem()
        if not item:
            QMessageBox.warning(self, "Erro", "Selecione um arquivo para excluir.")
            return

        display = item.text()
        nome_arquivo = display.split(" (")[0]

        reply = QMessageBox.question(self, "Confirmar Exclusão",
                                     f"Tem certeza que deseja excluir '{nome_arquivo}'?\nEsta ação não pode ser desfeita.",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.No:
            return

        cofre_path = obter_cofre_usuario(self.usuario)
        arquivo = os.path.join(cofre_path, nome_arquivo)

        try:
            if os.path.exists(arquivo):
                os.remove(arquivo)

            # Atualiza metadata
            metadata = obter_metadata_cofre(self.usuario)
            metadata["arquivos"] = [a for a in metadata["arquivos"] if a["nome"] != nome_arquivo]
            salvar_metadata_cofre(self.usuario, metadata)

            salvar_log(f"[COFRE] '{self.usuario}' excluiu '{nome_arquivo}'")
            QMessageBox.information(self, "Sucesso", f"Arquivo '{nome_arquivo}' excluído do cofre.")
            self.carregar_arquivos()
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao excluir arquivo:\n{e}")
            salvar_log(f"[COFRE] Erro ao excluir '{nome_arquivo}' por '{self.usuario}': {e}")

    def sair_cofre(self):
        encerrar_sessao(self.sessao_id)
        self.close()

# ------------------------- Painel do Colaborador -------------------------
class ColaboradorPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Painel do Colaborador")
        self.resize(500, 500)
        self.sessao_id = None  # Armazena ID da sessão após login facial

        layout = QVBoxLayout()

        # Título
        titulo = QLabel("🔐 Autenticação Facial")
        titulo.setAlignment(Qt.AlignCenter)
        titulo.setStyleSheet("font-size: 20px; font-weight: bold; color: #333; margin: 10px;")
        layout.addWidget(titulo)

        # Label informativo
        self.label = QLabel("Clique no botão abaixo para fazer login")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("font-size: 12px; color: #666; margin-bottom: 20px;")
        layout.addWidget(self.label)

        # Botão de login facial (principal)
        self.btn_face = QPushButton("📸 Fazer Login Facial")
        self.btn_face.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 8px;
                padding: 15px;
                font-weight: bold;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #3e8e41;
            }
        """)
        layout.addWidget(self.btn_face)

        # Label para mostrar usuário logado
        self.label_usuario = QLabel("")
        self.label_usuario.setAlignment(Qt.AlignCenter)
        self.label_usuario.setStyleSheet("font-size: 14px; font-weight: bold; color: #0078d7; margin: 10px;")
        self.label_usuario.setVisible(False)
        layout.addWidget(self.label_usuario)

        # Botão para acessar o cofre (inicialmente oculto)
        self.btn_cofre = QPushButton("🔒 Acessar Meu Cofre")
        self.btn_cofre.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border-radius: 8px;
                padding: 15px;
                font-weight: bold;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        self.btn_cofre.setVisible(False)
        layout.addWidget(self.btn_cofre)

        # Adiciona espaçamento para centralizar melhor
        layout.addStretch()

        self.setLayout(layout)

        self.btn_face.clicked.connect(self.login_facial)
        self.btn_cofre.clicked.connect(self.abrir_cofre)

    # ------------------------- Login por reconhecimento facial -------------------------
    def login_facial(self):
        video = None
        try:
            # Carrega usuários do JSON
            usuarios = carregar_usuarios()
            if not usuarios:
                QMessageBox.warning(self, "Erro", "Nenhum usuário cadastrado!")
                return

            # Converte embeddings armazenados para numpy arrays
            usuarios_processados = []
            for nome, info in usuarios.items():
                try:
                    emb = info.get("embedding", None)
                    if emb is None:
                        continue
                    usuarios_processados.append({
                        "nome": nome,
                        "embedding": np.array(emb) if isinstance(emb, (list, np.ndarray)) else None
                    })
                except Exception:
                    continue  # Pula usuários com embedding inválido

            if not usuarios_processados:
                QMessageBox.warning(self, "Erro", "Nenhum usuário possui reconhecimento facial cadastrado!\n\nCadastre a face dos usuários no Painel do Administrador.")
                return

            # Tenta abrir a câmera
            try:
                video = cv2.VideoCapture(0)
            except Exception as e:
                QMessageBox.critical(self, "Erro ao Acessar Câmera",
                                   f"Não foi possível inicializar a câmera.\n\n"
                                   f"Erro: {str(e)}\n\n"
                                   f"Verifique se:\n"
                                   f"• A câmera está conectada\n"
                                   f"• Nenhum outro programa está usando a câmera\n"
                                   f"• Você tem permissão para acessar a câmera")
                return

            if not video.isOpened():
                QMessageBox.critical(self, "Erro ao Acessar Câmera",
                                   "Não foi possível abrir a câmera!\n\n"
                                   "Possíveis causas:\n"
                                   "• Câmera está sendo usada por outro programa\n"
                                   "• Câmera não está conectada\n"
                                   "• Driver da câmera não está instalado\n"
                                   "• Permissões de acesso à câmera negadas")
                return

            QMessageBox.information(self, "Reconhecimento Facial", "📸 Olhe para a câmera para autenticação.\nPressione 'Q' na janela da câmera para cancelar.")

            usuario_identificado = None
            status_msg = "🔍 Procurando rostos..."
            font = cv2.FONT_HERSHEY_SIMPLEX
            frame_count = 0
            max_failed_frames = 30

            while True:
                try:
                    ret, frame = video.read()
                    if not ret:
                        frame_count += 1
                        if frame_count > max_failed_frames:
                            raise Exception("Falha ao capturar frames da câmera. A câmera pode ter sido desconectada.")
                        continue

                    frame_count = 0

                    # redimensiona frame para acelerar
                    small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
                    rgb = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

                    # Detecta rostos e gera embeddings
                    try:
                        faces = face_recognition.face_locations(rgb)
                        embeddings = face_recognition.face_encodings(rgb, faces)
                    except Exception as e:
                        raise Exception(f"Erro no processamento de reconhecimento facial: {str(e)}")

                    if len(faces) == 0:
                        status_msg = "❌ Nenhum rosto detectado"
                    else:
                        status_msg = "🔍 Rosto detectado, verificando..."

                    # compara embeddings com os usuários carregados
                    for rosto in embeddings:
                        for u in usuarios_processados:
                            if u["embedding"] is None:
                                continue
                            try:
                                match = face_recognition.compare_faces([u["embedding"]], rosto)[0]
                            except Exception:
                                # segurança caso formatos divergentes
                                match = False
                            if match:
                                usuario_identificado = u["nome"]
                                status_msg = f"✅ {usuario_identificado} reconhecido!"
                                break
                        if usuario_identificado:
                            break

                    # desenha mensagem sobre o frame
                    display_frame = cv2.resize(small_frame, (frame.shape[1], frame.shape[0]))
                    color = (0, 255, 0) if "✅" in status_msg else (0, 0, 255)
                    cv2.putText(display_frame, status_msg, (10, 30), font, 0.8, color, 2)

                    # Desenha retângulos ao redor dos rostos
                    for (top, right, bottom, left) in faces:
                        top *= 2
                        right *= 2
                        bottom *= 2
                        left *= 2
                        cv2.rectangle(display_frame, (left, top), (right, bottom), (255, 0, 0), 2)

                    try:
                        cv2.imshow("Reconhecimento Facial", display_frame)
                    except Exception as e:
                        raise Exception(f"Erro ao exibir janela de vídeo: {str(e)}")

                    key = cv2.waitKey(1) & 0xFF
                    if usuario_identificado or key == ord('q'):
                        break

                except Exception as e:
                    # Erro durante o loop
                    if video is not None:
                        video.release()
                    cv2.destroyAllWindows()
                    QMessageBox.critical(self, "Erro Durante Reconhecimento",
                                       f"Ocorreu um erro durante o reconhecimento:\n\n{str(e)}")
                    return

            # Libera recursos
            if video is not None:
                video.release()
            cv2.destroyAllWindows()

            if usuario_identificado:
                QMessageBox.information(self, "Acesso Liberado", f"✅ Acesso liberado para: {usuario_identificado}")

                # Armazena usuário atual
                self.usuario_atual = usuario_identificado

                # Atualiza label com nome do usuário
                self.label_usuario.setText(f"👤 Logado como: {usuario_identificado}")
                self.label_usuario.setVisible(True)

                # Cria sessão e habilita acesso ao cofre
                self.sessao_id = criar_sessao(usuario_identificado)
                self.btn_cofre.setVisible(True)

                # Log de acesso
                salvar_log(f"Colaborador '{usuario_identificado}' fez login facial.")
            else:
                QMessageBox.warning(self, "Falha", "Rosto não reconhecido ou operação cancelada.")

        except Exception as e:
            # Erro geral
            QMessageBox.critical(self, "Erro Inesperado",
                               f"Ocorreu um erro inesperado no reconhecimento facial:\n\n"
                               f"Erro: {str(e)}\n\n"
                               f"Tipo: {type(e).__name__}")
            try:
                if video is not None:
                    video.release()
                cv2.destroyAllWindows()
            except:
                pass

    # ------------------------- Abrir cofre -------------------------
    def abrir_cofre(self):
        if not self.sessao_id:
            QMessageBox.warning(self, "Erro", "Faça login facial primeiro para acessar o cofre!")
            return

        usuario = validar_sessao(self.sessao_id)
        if not usuario:
            QMessageBox.warning(self, "Sessão Expirada", "Sua sessão expirou. Faça login facial novamente.")
            self.sessao_id = None
            self.btn_cofre.setVisible(False)
            return

        self.cofre_window = CofrePanel(usuario, self.sessao_id)
        self.cofre_window.show()

# ------------------------- Menu Principal -------------------------
class MenuPrincipal(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistema de Cofre Digital com Reconhecimento Facial")
        self.resize(400, 220)
        layout = QVBoxLayout()

        title = QLabel("🔐 Cofre Digital Biométrico")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size:20px; font-weight:bold;")
        layout.addWidget(title)

        subtitle = QLabel("Sistema com Reconhecimento Facial")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("font-size:12px; color:#666; margin-bottom:15px;")
        layout.addWidget(subtitle)

        self.btn_admin = QPushButton("Painel do Administrador")
        self.btn_user = QPushButton("Painel do Colaborador")
        for b in [self.btn_admin, self.btn_user]:
            b.setStyleSheet("""
                QPushButton {
                    background-color: #0078d7;
                    color: white;
                    border: none;
                    padding: 12px;
                    border-radius: 8px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #005fa3;
                }
            """)
            layout.addWidget(b)

        self.setLayout(layout)
        self.btn_admin.clicked.connect(self.abrir_admin)
        self.btn_user.clicked.connect(self.abrir_colab)

    def abrir_admin(self):
        self.admin = AdminPanel()
        self.admin.show()

    def abrir_colab(self):
        self.colab = ColaboradorPanel()
        self.colab.show()

# ------------------------- Execução -------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    janela = MenuPrincipal()
    janela.show()
    sys.exit(app.exec_())
