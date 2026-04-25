# MetePDF

Converta TXT, imagens (PNG/JPG), DOCX e PDF para PDF — via interface gráfica ou linha de comando.

## Instalação

### Recomendado — `uv` (mais rápido)

Com o Claude Code aberto neste projeto, execute:

```
/install
```

O comando instala o `uv` automaticamente se necessário, cria o virtualenv e instala todas as dependências.

### Manual — uv

```bash
# Instalar uv (uma vez)
# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
# Linux / macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# Criar venv + instalar dependências
uv venv .venv
uv pip install -r requirements.txt --python .venv

# Ativar
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate
```

### Manual — pip

```bash
pip install -r requirements.txt
```

> **Windows + DOCX:** o `docx2pdf` requer o Microsoft Word instalado.  
> **Linux/macOS + DOCX:** instale o LibreOffice (`sudo apt install libreoffice` ou `brew install libreoffice`).

---

## Interface gráfica (GUI)

```bash
python gui.py
```

- Arraste arquivos ou pastas para a janela (ou use os botões)
- Escolha o diretório de saída
- Clique em **Converter →**
- Acompanhe o progresso em tempo real na fila de arquivos
- Cancele a qualquer momento com o botão **Cancelar**
- Ao fim, abra a pasta de saída com um clique

---

## Linha de comando (CLI)

```bash
# Arquivo único
python main.py documento.docx

# Vários arquivos
python main.py arquivo1.txt arquivo2.png arquivo3.jpg

# Diretório inteiro
python main.py input/

# Varredura recursiva de subpastas
python main.py input/ --recursive

# Diretório de saída personalizado
python main.py input/ --output resultados/

# Log detalhado
python main.py input/ --verbose
```

---

## Formatos suportados

| Extensão | Estratégia |
|----------|-----------|
| `.txt` | reportlab — preserva quebras de linha, layout A4 |
| `.png` `.jpg` `.jpeg` | Pillow + reportlab — centralizado, proporção mantida |
| `.docx` | docx2pdf (Word no Windows, LibreOffice no Unix) |
| `.pdf` | PyMuPDF — validação e cópia |

---

## Estrutura do projeto

```
metepdf/
├── gui.py                   # Interface gráfica (customtkinter)
├── main.py                  # CLI
├── requirements.txt
├── pyproject.toml
├── metepdf.spec             # Configuração PyInstaller
├── generate_icon.py         # Geração do ícone .ico
├── converters/
│   ├── base.py              # Classe abstrata BaseConverter
│   ├── txt_converter.py     # TXT → PDF (reportlab)
│   ├── image_converter.py   # PNG/JPG → PDF (Pillow + reportlab)
│   ├── docx_converter.py    # DOCX → PDF (docx2pdf)
│   └── pdf_converter.py     # PDF → validação + cópia (PyMuPDF)
├── core/
│   ├── dispatcher.py        # Roteador: escolhe o conversor pelo formato
│   ├── service.py           # ConversionService — backend compartilhado por GUI e CLI
│   └── exceptions.py        # Hierarquia de exceções
├── utils/
│   └── file_utils.py        # Helpers de caminho e coleta de arquivos
├── assets/
│   └── icon.ico             # Ícone da aplicação
├── input/                   # Pasta de entrada padrão
└── output/                  # PDFs gerados
```

---

## Arquitetura

A conversão é centralizada em `core/service.py`. Tanto a GUI quanto a CLI usam o mesmo `ConversionService`, sem duplicação de lógica.

```
GUI (gui.py)  ──┐
                ├──► ConversionService ──► Dispatcher ──► Converters
CLI (main.py) ──┘
```

`ConversionService` suporta callbacks de progresso e cancelamento:

```python
from core.service import ConversionService
from pathlib import Path

service = ConversionService(output_dir=Path("output"))

def progresso(done, total, result):
    status = "OK" if result.success else f"FALHOU: {result.error}"
    print(f"[{done}/{total}] {result.input_path.name} — {status}")

results = service.convert_files(
    files=[Path("documento.txt"), Path("foto.png")],
    on_progress=progresso,
)
```

Para rodar em background (como a GUI faz):

```python
service.convert_files(files, on_progress=..., on_done=..., threaded=True)
# retorna imediatamente; callbacks são chamados na thread de conversão
```

Para cancelar:

```python
service.cancel()  # interrompe a fila após o arquivo atual
```

---

## Adicionar um novo conversor

1. Crie `converters/meu_formato_converter.py` estendendo `BaseConverter`:

```python
from pathlib import Path
from converters.base import BaseConverter

class MeuFormatoConverter(BaseConverter):
    def convert(self, input_path: Path, output_path: Path) -> None:
        self._ensure_output_dir(output_path)
        # lógica de conversão aqui
```

2. Registre a extensão em `core/dispatcher.py`:

```python
from converters.meu_formato_converter import MeuFormatoConverter

_REGISTRY: dict[str, type[BaseConverter]] = {
    # ...
    ".meuformato": MeuFormatoConverter,
}
```

Pronto — GUI e CLI passam a reconhecer o novo formato automaticamente.

---

## Gerar executável (.exe)

```
/build
```

Ou manualmente:

```bash
python generate_icon.py          # gera assets/icon.ico
pyinstaller metepdf.spec         # gera dist/MetePDF.exe
```

O executável não inclui Word ou LibreOffice. Se a conversão de `.docx` for necessária, o usuário precisa ter um deles instalado.
