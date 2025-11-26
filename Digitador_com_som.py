import asyncio
import pathlib
import random
import re
from typing import ClassVar

# --- Importações para Áudio ---
# Lembre-se: quem baixar precisará rodar "pip install pygame"
import pygame 
# --- Fim Importações para Áudio ---

from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType
from textual.widgets import TextArea, Footer
from textual.worker import Worker, WorkerState

# --- Configurações ---
# AJUSTE 1: Usa o próprio arquivo Python como texto para digitar (para evitar erro em outros PCs)
# Se quiser outro arquivo, coloque-o na mesma pasta e mude o nome abaixo.
CURRENT_DIR = pathlib.Path(__file__).parent
CODE_PATH = CURRENT_DIR / "Digitador_com_som.py" 

SPEED = 0.35  
LEXER = "python" # Mudamos para python pois ele vai ler a si mesmo

# --- Configurações de Áudio ---
# AJUSTE 2: Pega o som da mesma pasta onde o script está salvo
SOUND_FILE = CURRENT_DIR / "typing_sound.wav"
# --- Fim Configurações de Áudio ---

# --- Tratamento do Arquivo ---
RE_SPACES_TO_TAB = re.compile(r" {4}")
try:
    CODE = CODE_PATH.read_text("utf-8", errors="ignore").strip()
    CODE = RE_SPACES_TO_TAB.sub("\t", CODE)
except FileNotFoundError:
    CODE = "-- Arquivo não encontrado.\n-- O script tentou ler a si mesmo mas falhou."
    LEXER = "text"

# --- Utilitários ---
system_random = random.SystemRandom()

# --- Componentes Textual ---

class ExtendedTextArea(TextArea):
    def on_mount(self) -> None:
        self.can_focus = False
        self.can_focus_children = False
        self.theme = "dracula"
        self.language = LEXER
        self.show_line_numbers = True
        self.tab_behavior = "indent"
        self.highlight_cursor_line = True
        
    def on_mouse_down(self, event) -> None:
        event.prevent_default()

    def on_key(self, event) -> None:
        event.prevent_default()

    def type_char(self, char: str) -> None:
        self.insert(char)
        self.scroll_end()

class TyperApp(App):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("ctrl+q", "quit", "Sair", priority=True),
        Binding("space", "toggle_pause", "Pausar/Continuar", priority=True),
        Binding("s", "start_stream", "Iniciar Digitação", priority=False),
    ]
    
    CSS = """
    #editor {
        border: none;
        padding: 1 1 2 1;
        background: rgba(0, 0, 0, 0);
    }
    """
    
    def compose(self) -> ComposeResult:
        self.editor = ExtendedTextArea(id="editor")
        yield self.editor
        yield Footer()

    def on_mount(self) -> None:
        self.is_paused = True
        self.typer_worker: Worker | None = None
        self.editor.load_text(f"Pressione 'S' para digitar.\n'Espaço' para Pausar.")
        self.editor.move_cursor((0, 0))
        
        # --- Inicialização do Áudio ---
        try:
            pygame.mixer.init()
            # Verifica se o arquivo existe antes de carregar
            if SOUND_FILE.exists():
                self.typing_sound = pygame.mixer.Sound(str(SOUND_FILE))
                self.sound_enabled = True
            else:
                self.notify(f"Arquivo de som não encontrado: {SOUND_FILE.name}", severity="error")
                self.sound_enabled = False
        except pygame.error as e:
            self.notify(f"Erro ao inicializar áudio: {e}. Som desativado.", severity="error")
            self.sound_enabled = False
        except Exception as e:
             self.notify(f"Erro genérico de áudio: {e}", severity="error")
             self.sound_enabled = False
        # --- Fim Inicialização do Áudio ---

    def action_quit(self) -> None:
        if self.typer_worker:
            self.typer_worker.cancel()
        
        if hasattr(self, 'sound_enabled') and self.sound_enabled:
            pygame.mixer.quit()
        
        self.exit()

    def action_toggle_pause(self) -> None:
        if not self.typer_worker or self.typer_worker.state != WorkerState.RUNNING:
            return
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.notify("Pausado.", severity="warning")
        else:
            self.notify("Continuando...", severity="information")

    def action_start_stream(self) -> None:
        if self.typer_worker and self.typer_worker.state == WorkerState.RUNNING:
            return
        self.editor.clear()
        self.is_paused = False
        self.typer_worker = self.run_worker(self.typer_stream, exclusive=True, group="typer")

    def make_sound(self, char):
        if not self.sound_enabled:
            return

        volume = random.uniform(0.1, 0.3)
        self.typing_sound.set_volume(volume)
        self.typing_sound.play(loops=0)

    async def typer_stream(self) -> None:
        for char in CODE:
            while self.is_paused:
                await asyncio.sleep(0.1)
            
            rand = system_random.uniform(0.001, 0.04)
            if char in " \n\t":
                rand *= 4 
            
            try:
                await asyncio.to_thread(self.make_sound, char)
            except Exception:
                pass 
            
            await asyncio.sleep(rand / SPEED)
            
            self.editor.type_char(char)
            
        self.notify("Digitação concluída!", severity="success")
        self.is_paused = True

if __name__ == "__main__":
    app = TyperApp()
    app.run()