import os, sys
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QGraphicsOpacityEffect,
    QStackedWidget,
    QFrame,
    QLabel,
    QGridLayout,
    QPushButton,
    QSizePolicy,
    QLayout,
)
from PySide6.QtCore import (
    Qt,
    QTimer,
    QPropertyAnimation,
    QEasingCurve,
    QSequentialAnimationGroup,
    QParallelAnimationGroup,
    QPauseAnimation,
    QAbstractAnimation,
    QPoint,
)
from PySide6.QtGui import QShortcut, QKeySequence, QDesktopServices, QColor
from PySide6.QtCore import (
    Qt,
    QTimer,
    QPropertyAnimation,
    QEasingCurve,
    QSequentialAnimationGroup,
    QParallelAnimationGroup,
    QPauseAnimation,
    QAbstractAnimation,
    QPoint,
    QUrl,
)

from Screen import Ui_Dialog
from PySide6.QtWidgets import QMessageBox, QGraphicsDropShadowEffect
from ui_loader import carregar_ui
from SkillExcel import atualizar_planilha_por_projetos, calcular_progressos

# Base do projeto, independente de onde você rodar
BASE_DIR = Path(__file__).resolve().parent
MAX_PROJETOS_POR_SKILL = 50


def skill_to_folder(skill: str) -> Path:
    # mesma convenção que você já usa no preencher_grid_projetos: "Excel", "Powerbi", etc.
    cap = (skill or "").strip()
    if not cap:
        return BASE_DIR / "Projetos" / cap
    return BASE_DIR / "Projetos" / (cap[:1].upper() + cap[1:].lower())


def contar_projetos(skill: str) -> int:
    """Conta subpastas imediatas em Projetos/<SkillCap>."""
    pasta = skill_to_folder(skill)
    if not pasta.exists():
        return 0
    try:
        return sum(1 for p in pasta.iterdir() if p.is_dir())
    except Exception:
        return 0


def calcular_progressos(skills: list[str]) -> dict:
    """
    Retorna: { skill: {'count':int, 'faltam':int, 'percent':int} }
    """
    out = {}
    for s in skills:
        c = contar_projetos(s)
        faltam = max(0, MAX_PROJETOS_POR_SKILL - c)
        percent = min(100, round((c / MAX_PROJETOS_POR_SKILL) * 100))
        out[s] = {"count": c, "faltam": faltam, "percent": percent}
    return out


def abspath(*parts: str) -> str:
    return str(BASE_DIR.joinpath(*parts))


def abrir_pasta(p: Path, parent=None):
    if not p.exists():
        QMessageBox.warning(
            parent, "Pasta não encontrada", f"Não encontrei a pasta:\n{p}"
        )
        return
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(p)))


def _hex_to_rgb(hx: str):
    hx = hx.strip().lstrip("#")
    if len(hx) == 3:
        hx = "".join(c * 2 for c in hx)
    r = int(hx[0:2], 16)
    g = int(hx[2:4], 16)
    b = int(hx[4:6], 16)
    return r, g, b


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return "#{:02x}{:02x}{:02x}".format(
        max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))
    )


def _blend(rgb, factor: float, to_white=True):
    """factor 0..1: aproxima de branco (to_white=True) ou preto (False)."""
    r, g, b = rgb
    if to_white:
        return (
            int(r + (255 - r) * factor),
            int(g + (255 - g) * factor),
            int(b + (255 - b) * factor),
        )
    else:
        return (int(r * (1 - factor)), int(g * (1 - factor)), int(b * (1 - factor)))


def _auto_text_color(rgb) -> str:
    # luminância relativa aproximada -> escolhe preto ou branco
    r, g, b = [c / 255 for c in rgb]
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return "#000000" if lum > 0.6 else "#ffffff"


def make_button_qss(base_hex: str) -> str:
    base_rgb = _hex_to_rgb(base_hex)
    text_hex = _auto_text_color(base_rgb)
    hover_rgb = _blend(base_rgb, 0.18, to_white=True)  # 18% mais claro
    press_rgb = _blend(base_rgb, 0.18, to_white=False)  # 18% mais escuro
    hover_hex = _rgb_to_hex(*hover_rgb)
    press_hex = _rgb_to_hex(*press_rgb)
    focus_hex = hover_hex

    return f"""
        QPushButton {{
            background-color: {base_hex};
            color: {text_hex};
            border: 1px solid transparent;
            border-radius: 6px;
            padding: 6px 12px;
            font-weight: 600;
        }}
        QPushButton:hover {{
            background-color: {hover_hex};
            color: {text_hex};
            border: 1px solid {focus_hex};
        }}
        QPushButton:focus {{
            border: 2px solid {focus_hex};
        }}
        QPushButton:pressed {{
            background-color: {press_hex};
            color: {text_hex};
        }}
        QPushButton:disabled {{
            background-color: #555;
            color: #bbb;
            border: 1px solid #555;
        }}
    """


def make_scrollbar_qss(color_hex: str) -> str:
    return f"""
        QScrollBar:vertical {{
           background: #111;
            width: 7px;
            margin: 4px 0 4px 0;
            border-radius: 6px;
        }}
        QScrollBar::handle:vertical {{
            background: {color_hex};
            border-radius: 6px;
           min-height: 30px;
        }}
        QScrollBar::handle:vertical:hover {{
        background: {_rgb_to_hex(*_blend(_hex_to_rgb(color_hex), 0.25, True))};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            background: none;
            height: 0px;
        }}
        QScrollBar:horizontal {{
            background: #111;
            height: 7px;
            margin: 0 4px 0 4px;
            border-radius: 6px;
        }}
        QScrollBar::handle:horizontal {{
            background: {color_hex};
            border-radius: 6px;
            min-width: 30px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: {_rgb_to_hex(*_blend(_hex_to_rgb(color_hex), 0.25, True))};
        }}
        """


def make_menu_button_qss(color_hex: str) -> str:
    rgb = _hex_to_rgb(color_hex)
    text_hex = _auto_text_color(rgb)

    hover_rgba = f"rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, 0.18)"  # leve brilho no hover
    focus_rgba = f"rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, 0.35)"  # cor aparece ao focar
    pressed_rgba = f"rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, 0.55)"  # mais forte ao clicar

    return f"""
        /* Estado normal: invisível (transparente) */
        QPushButton {{
            background-color: transparent;
            color: rgba(255, 255, 255, 0.8);  /* texto branco semi-transparente */
            border: 2px solid transparent;    /* sem borda */
            border-radius: 10px;
            padding: 8px 14px;
            font-weight: 700;
        }}

        /* Hover: brilho leve da cor */
        QPushButton:hover {{
            background-color: {hover_rgba};
            color: {text_hex};
            border: 2px solid transparent;
        }}

        /* Foco: cor da skill aparece */
        QPushButton:focus {{
            background-color: {focus_rgba};
            color: {text_hex};
            border: 2px solid {color_hex};
        }}

        /* Pressionado: mais intenso */
        QPushButton:pressed {{
            background-color: {pressed_rgba};
            color: {text_hex};
            border: 2px solid {color_hex};
        }}

        /* Desativado */
        QPushButton:disabled {{
            background-color: transparent;
            color: rgba(180,180,180,0.4);
            border: 2px solid transparent;
        }}
    """


# ==============================================================
# Função → Rolagem suave
# ==============================================================
def scroll_suave(scrollArea, destino, duracao=600):
    anim = QPropertyAnimation(scrollArea.verticalScrollBar(), b"value")
    anim.setDuration(duracao)
    anim.setStartValue(scrollArea.verticalScrollBar().value())
    anim.setEndValue(destino)
    anim.setEasingCurve(QEasingCurve.OutCubic)
    anim.start()
    scrollArea._animacao_scroll = anim


# ==============================================================
# Função → Preencher grid de projetos com layout responsivo
# ==============================================================
def preencher_grid_projetos(
    tela,
    skill: str,
    btn_hex: str = "#00b894",
    atraso_entre_cards_ms=10,
    dur_ms=200,
    desloc_px=14,
):
    from pathlib import Path

    skill_cap = skill[:1].upper() + skill[1:].lower()
    pasta = Path(BASE_DIR, "Projetos", skill_cap)
    if not pasta.exists():
        print(f"[ERRO] Pasta não encontrada: {pasta}")
        QMessageBox.critical(
            tela, "Pasta não encontrada", f"Não achei a pasta:\n{pasta}"
        )
        return

    tela.scrollArea.setWidgetResizable(True)
    scroll_widget = tela.scrollAreaWidgetContents

    # limpa conteúdo anterior
    old = scroll_widget.layout()
    if old:
        while old.count():
            it = old.takeAt(0)
            w = it.widget()
            if w:
                w.deleteLater()
        old.deleteLater()

    # parâmetros visuais
    CARD_W, CARD_H = 206, 110
    H_SP, V_SP = 20, 24
    M_LEFT, M_TOP, M_RIGHT, M_BOTTOM = 24, 24, 24, 24

    grid = QGridLayout(scroll_widget)
    grid.setContentsMargins(M_LEFT, M_TOP, M_RIGHT, M_BOTTOM)
    grid.setHorizontalSpacing(H_SP)
    grid.setVerticalSpacing(V_SP)
    grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
    grid.setSizeConstraint(QLayout.SetMinimumSize)

    subpastas = sorted([n.name for n in pasta.iterdir() if n.is_dir()])
    slots, cards = [], []

    if hasattr(tela, "_anim_refs"):
        for grp in tela._anim_refs:
            try:
                grp.stop()
            except Exception:
                pass
        tela._anim_refs.clear()
    else:
        tela._anim_refs = []

    for nome in subpastas:
        slot = QFrame(scroll_widget)
        slot.setFixedSize(CARD_W, CARD_H)
        slot.setStyleSheet("background: transparent;")

        card = QFrame(slot)
        card.setObjectName("cardProjeto")
        card.setGeometry(0, desloc_px, CARD_W, CARD_H)
        card.setStyleSheet(
            f"""
            QFrame#cardProjeto {{
                background-color: rgba(40, 40, 40, 0.75);
                border: 1px solid #555;
        border-radius: 10px;
            }}
            QFrame#cardProjeto:hover {{
                border: 2px solid {btn_hex};
                background-color: rgba(60, 60, 60, 0.9);
            }}
        """
        )

        label = QLabel(nome, card)
        label.setAlignment(Qt.AlignCenter)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        label.setStyleSheet(
            """
            color: white;
            font-size: 13px;
            font-weight: bold;
            padding: 2px;
        """
        )
        label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        botao = QPushButton("Abrir", card)
        botao.setCursor(Qt.PointingHandCursor)
        botao.setStyleSheet(make_button_qss(btn_hex))  # <— usa a cor da skill
        botao.setFocusPolicy(Qt.StrongFocus)  # necessário pro :focus
        botao.setStyleSheet(make_button_qss(btn_hex))

        # caminho da subpasta daquele card
        caminho_subpasta = pasta / nome
        botao.clicked.connect(lambda _, p=caminho_subpasta: abrir_pasta(p, tela))

        lay = QGridLayout(card)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.addWidget(label, 0, 0, Qt.AlignCenter)
        lay.addWidget(botao, 1, 0, Qt.AlignCenter)

        eff = QGraphicsOpacityEffect(card)
        eff.setOpacity(0.0)
        card.setGraphicsEffect(eff)

        slots.append(slot)
        cards.append(card)

    # === Recalcula colunas conforme tamanho da janela ===
    def relayout():
        avail = tela.scrollArea.viewport().width() - (M_LEFT + M_RIGHT)
        colunas = max(1, (avail + H_SP) // (CARD_W + H_SP))
        while grid.count():
            grid.takeAt(0)
        for i, slot in enumerate(slots):
            grid.addWidget(slot, i // colunas, i % colunas)
        rows = (len(slots) + colunas - 1) // colunas
        total_h = (rows * CARD_H) + max(0, rows - 1) * V_SP + M_TOP + M_BOTTOM
        scroll_widget.setMinimumHeight(total_h)

    relayout()

    old_resize = tela.scrollArea.resizeEvent

    def on_resize(ev):
        relayout()
        if old_resize:
            old_resize(ev)

    tela.scrollArea.resizeEvent = on_resize

    # animação
    def animar(i=0):
        if i >= len(cards):
            return
        c = cards[i]
        eff = c.graphicsEffect()
        fade = QPropertyAnimation(eff, b"opacity", tela)
        fade.setDuration(dur_ms)
        fade.setStartValue(0.0)
        fade.setEndValue(1.0)
        fade.setEasingCurve(QEasingCurve.OutCubic)

        slide = QPropertyAnimation(c, b"pos", tela)
        slide.setDuration(dur_ms)
        slide.setStartValue(QPoint(0, desloc_px))
        slide.setEndValue(QPoint(0, 0))
        slide.setEasingCurve(QEasingCurve.OutCubic)

        grp = QParallelAnimationGroup(tela)
        grp.addAnimation(fade)
        grp.addAnimation(slide)
        tela._anim_refs.append(grp)
        grp.finished.connect(
            lambda: QTimer.singleShot(atraso_entre_cards_ms, lambda: animar(i + 1))
        )
        grp.start()

    QTimer.singleShot(120, lambda: animar(0))
    print(f"[OK] {len(subpastas)} projetos carregados e animados.")


# ==============================================================
# Classe Principal
# ==============================================================
class MainWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        self.resize(1200, 800)
        self.setFixedSize(self.size())
        self.setWindowTitle("Portfólio")
        # ===== Cores / skills =====
        self.skill_btn_colors = {
            "excel": "#00ff62",
            "powerbi": "#f2c811",
            "vba": "#9000f0",
            "sql": "#00a2ff",
            "java": "#ff0000",
            "python": "#f2c811",
            "ia": "#9000f0",
            "redes": "#00a2ff",
            "process": "#ff0000",
        }
        self.skills = [
            "excel",
            "powerbi",
            "vba",
            "sql",
            "java",
            "python",
            "ia",
            "redes",  # <- redes antes
            "process",  # <- process depois
        ]
        # Ordem que o btnProx deve seguir
        self.sequence_order = [
            "excel",
            "powerbi",
            "vba",
            "sql",
            "java",
            "python",
            "ia",
            "redes",
            "process",
        ]

        # Ordem específica para a animação (se quiser controlar independente do self.skills)
        self.anim_order = [
            "excel",
            "powerbi",
            "vba",
            "sql",
            "java",
            "python",
            "ia",
            "redes",
            "process",  # aqui você decide a ordem visual
        ]

        try:
            from SkillExcel import atualizar_planilha_por_projetos, calcular_progressos
        except ImportError:
            print(
                "[AVISO] Não encontrei planilha_utils.py, pulando atualização automática."
            )
        else:
            # Atualiza a planilha (grava colunas projects/missing/percent)
            atualizar_planilha_por_projetos(
                self.skills, sobrescrever_value_com_percent=True
            )

            # Atualiza as barras do menu inicial, se existirem
            progresso = calcular_progressos(self.skills)
            for skill, info in progresso.items():
                barra = getattr(self.ui, skill, None)
                if barra and hasattr(barra, "setValue"):
                    try:
                        barra.setValue(info["percent"])
                    except Exception:
                        pass
        # ===== Container principal =====
        self.container = QStackedWidget(self)
        layout_principal = QGridLayout(self)
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.addWidget(self.container)
        self.setLayout(layout_principal)

        if hasattr(self.ui, "framePrincipal"):
            self.container.addWidget(self.ui.framePrincipal)

        # ===== Atalhos =====
        QShortcut(QKeySequence("F11"), self, activated=self.toggle_fullscreen)
        QShortcut(QKeySequence("Ctrl+M"), self, activated=self.showMinimized)
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self.showMaximized)

        # ===== Intro / animações =====
        self.anim_seq = None
        self.intro_built = False
        self.intro_started = False
        self._build_intro_sequence()

        # ===== Liga botões do menu às telas específicas (se quiser abrir direto) =====
        for s in self.skills:
            btn = getattr(self.ui, f"btn{s}", None)
            if btn:
                ui_path = abspath("telas", f"{s}.ui")
                btn.clicked.connect(lambda _, p=ui_path: self.abrir_tela(p))

                cor = self.skill_btn_colors.get(s, "#00b894")
                btn.setStyleSheet(make_menu_button_qss(cor))
                btn.setAutoDefault(False)
                btn.setDefault(False)
                btn.setCheckable(False)
                btn.setDown(False)
                btn.setFocusPolicy(Qt.NoFocus)
                btn.clearFocus()

        # ===== Navegação sequencial por .ui (TELAS/telas) =====
        self._telas_dir = next(
            (p for p in [BASE_DIR / "TELAS", BASE_DIR / "telas"] if p.exists()), None
        )
        self._telas = []
        self._current_tela_idx = -1  # -1 = ainda no menu

        if self._telas_dir is None:
            print(
                "[AVISO] Pasta TELAS/telas não encontrada. Navegação por 'btnProx' desativada."
            )
        else:
            self._indexar_telas()
        # btnProx no menu principal (se existir)
        btnProx_menu = getattr(self.ui, "btnProx", None)
        if btnProx_menu:
            btnProx_menu.clicked.connect(self.next_tela)

    # === Helpers de animação (iguais aos seus) ===
    def _collect_intro_targets(self):
        if hasattr(self, "_paineis"):
            return
        self._paineis = []
        for i in range(1, 50):
            p = getattr(self.ui, f"painel{i}", None)
            if not p:
                break
            self._paineis.append(p)

        self._btns = []
        self._barras = []
        self._barras_final = {}

        order = getattr(
            self, "anim_order", self.skills
        )  # cai pra self.skills se não houver anim_order

        for s in order:
            btn = getattr(self.ui, f"btn{s}", None)
            if btn:
                self._btns.append(btn)

            barra = getattr(self.ui, s, None)
            if barra and hasattr(barra, "value"):
                self._barras.append(barra)
                self._barras_final[s] = barra.value()

    def _reset_intro_widgets(self):
        for w in getattr(self, "_paineis", []):
            if not w.graphicsEffect():
                w.setGraphicsEffect(QGraphicsOpacityEffect(self))
            if isinstance(w.graphicsEffect(), QGraphicsOpacityEffect):
                w.graphicsEffect().setOpacity(0.0)

        for btn in getattr(self, "_btns", []):
            if not btn.graphicsEffect():
                btn.setGraphicsEffect(QGraphicsOpacityEffect(self))
            eff = btn.graphicsEffect()
            if isinstance(eff, QGraphicsOpacityEffect):
                eff.setOpacity(0.0)

        for barra in getattr(self, "_barras", []):
            if not barra.graphicsEffect():
                barra.setGraphicsEffect(QGraphicsOpacityEffect(self))
            if isinstance(barra.graphicsEffect(), QGraphicsOpacityEffect):
                barra.graphicsEffect().setOpacity(0.0)
            try:
                barra.setValue(0)
            except Exception:
                pass

    def _build_intro_sequence(self):
        if self.intro_built:
            return
        self._collect_intro_targets()
        self._reset_intro_widgets()
        self.anim_seq = QSequentialAnimationGroup(self)
        total = max(len(self._paineis), len(self._btns), len(self._barras))

        def _fade_for_if_opacity(w):
            eff = w.graphicsEffect() if w else None
            if not isinstance(eff, QGraphicsOpacityEffect):
                return None
            fade = QPropertyAnimation(eff, b"opacity", self)
            fade.setDuration(250)
            fade.setStartValue(0.0)
            fade.setEndValue(1.0)
            fade.setEasingCurve(QEasingCurve.OutCubic)
            return fade

        for i in range(total):
            group = QParallelAnimationGroup(self)

            p = self._paineis[i] if i < len(self._paineis) else None
            b = self._btns[i] if i < len(self._btns) else None
            br = self._barras[i] if i < len(self._barras) else None

            for target in (p, b, br):
                fade = _fade_for_if_opacity(target)
                if fade:
                    group.addAnimation(fade)

            if br and hasattr(br, "value"):
                key = None
                for k in self.skills:
                    if getattr(self.ui, k, None) is br:
                        key = k
                        break
                fill = QPropertyAnimation(br, b"value", self)
                fill.setDuration(400)
                fill.setStartValue(0)
                fill.setEndValue(self._barras_final.get(key, 0))
                fill.setEasingCurve(QEasingCurve.InOutCubic)
                group.addAnimation(fill)

            if group.animationCount():
                self.anim_seq.addAnimation(group)
                self.anim_seq.addAnimation(QPauseAnimation(200, self))

        self.intro_built = True

    # ===== Indexação e navegação sequencial =====
    def _indexar_telas(self):
        # Prioriza a pasta "telas" (ou "TELAS") que você já detectou
        base = self._telas_dir or (BASE_DIR / "telas")
        self._telas = []

        # 1) Telas na ordem declarada
        for name in getattr(self, "sequence_order", []):
            p = base / f"{name}.ui"
            if p.exists():
                self._telas.append(str(p))

        # 2) (Opcional) incluir quaisquer .ui extras que existam e não estejam na ordem
        extras = []
        try:
            all_ui = [str(p) for p in base.glob("*.ui")]
            known = set(
                map(lambda s: os.path.normcase(os.path.abspath(s)), self._telas)
            )
            for ui in all_ui:
                npath = os.path.normcase(os.path.abspath(ui))
                if npath not in known:
                    extras.append(ui)
        except Exception:
            pass

        # Anexa extras ao final, se quiser:
        self._telas.extend(sorted(extras, key=lambda s: s.lower()))

        print(f"[TELAS] Ordem final ({len(self._telas)}):")
        for i, t in enumerate(self._telas):
            print(f"  {i+1:02d} -> {Path(t).stem}")

    # ----------------------------------------------------------
    def toggle_fullscreen(self):
        self.showNormal() if self.isFullScreen() else self.showFullScreen()

    def showEvent(self, event):
        super().showEvent(event)
        if not self.intro_started and self.anim_seq:
            self.intro_started = True
            QTimer.singleShot(0, self.anim_seq.start)

    def abrir_tela(self, caminho_ui: str):
        print(f"[DEBUG] Abrindo tela: {caminho_ui}")

        if self.anim_seq and self.anim_seq.state() == QAbstractAnimation.Running:
            self.anim_seq.stop()
            self.intro_started = True

        if not os.path.exists(caminho_ui):
            QMessageBox.critical(
                self, "Arquivo não encontrado", f"Não achei o UI:\n{caminho_ui}"
            )
            return

        try:
            nova_tela = carregar_ui(caminho_ui)
        except Exception as e:
            QMessageBox.critical(
                self, "Erro ao carregar UI", f"{e}\n\nCaminho: {caminho_ui}"
            )
            return

        self.container.addWidget(nova_tela)
        self.container.setCurrentWidget(nova_tela)

        # Atualiza o índice se a abertura foi direta
        try:
            if self._telas:
                path_norm = os.path.normcase(os.path.abspath(caminho_ui))
                for i, p in enumerate(self._telas):
                    if os.path.normcase(os.path.abspath(p)) == path_norm:
                        self._current_tela_idx = i
                        break
        except Exception:
            pass

        # Voltar / Próximo embutidos na tela, se existirem
        if hasattr(nova_tela, "btnVoltar"):
            try:
                nova_tela.btnVoltar.clicked.disconnect()
            except Exception:
                pass
            nova_tela.btnVoltar.clicked.connect(self.voltar)

        if hasattr(nova_tela, "btnProx"):
            try:
                nova_tela.btnProx.clicked.disconnect()
            except Exception:
                pass
            nova_tela.btnProx.clicked.connect(self.next_tela)

        # Detecção de skill para preencher grid (se for tela de skill)
        stem = Path(caminho_ui).stem.lower()
        if stem in self.skills:
            cor = self.skill_btn_colors.get(stem, "#00b894")
            preencher_grid_projetos(nova_tela, stem, btn_hex=cor)
            nova_tela.setStyleSheet(nova_tela.styleSheet() + make_scrollbar_qss(cor))

    def next_tela(self):
        if not self._telas:
            QMessageBox.information(
                self, "Sem telas", "Nenhum .ui encontrado em TELAS."
            )
            return
        self._current_tela_idx = (self._current_tela_idx + 1) % len(self._telas)
        self.abrir_tela(self._telas[self._current_tela_idx])

    def voltar(self):
        print("[DEBUG] Voltou ao menu principal")
        self.container.setCurrentWidget(self.ui.framePrincipal)
        self.intro_started = False
        self._reset_intro_widgets()
        if not self.anim_seq:
            self.intro_built = False
            self._build_intro_sequence()
        QTimer.singleShot(150, self.anim_seq.start)

    def atualizar_barras_por_projetos(self):
        """
        Ajusta as barras (self.ui.<skill>) para a % baseada nas pastas em Projetos/<Skill>.
        Se a barra não existir, ignora.
        """
        if not hasattr(self, "skills"):
            return
        prog = calcular_progressos(self.skills)
        for s, info in prog.items():
            barra = getattr(self.ui, s, None)  # você já usa esse padrão
            if barra and hasattr(barra, "setValue"):
                try:
                    barra.setValue(int(info["percent"]))
                except Exception:
                    pass


# ==============================================================
# Execução
# ==============================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
