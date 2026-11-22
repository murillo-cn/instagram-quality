<div align="center">

# Instagram Quality

**Prepare seus vídeos para o Instagram sem perder nitidez, cor nem detalhe.**

App gratuito e open source para Windows: ajusta, analisa e converte vídeos para 1080×1920 H.264, com comparação antes/depois ao vivo.

[**Baixar o instalador**](../../releases/latest) · [Como usar](#como-usar) · [Rodar pelo código](#rodar-pelo-código)

</div>

---

## Por que existe

O Instagram recomprime todo vídeo que você posta, e o resultado costuma ser borrado, sem brilho e com degradês quebrados em faixas. O Instagram Quality entrega o arquivo **já no formato que a plataforma espera** (1080×1920, H.264, bitrate alto), com nitidez e cor reforçadas, para a recompressão estragar o mínimo possível.

## Recursos

| | |
|---|---|
| **Predefinições** | Equilibrado (recomendado), Só converter, Nítido + cor, Máximo detalhe e Limpar vídeo ruidoso. Dá pra salvar as suas. |
| **Nitidez** | Sharpen, High-pass (realça textura) e CAS (só onde falta detalhe). |
| **Cor** | Contraste, saturação, gamma, brilho, vibrance e conversão **HDR → SDR**. |
| **Limpeza** | Redução de ruído, grão (esconde blocos e degradês) e deband. |
| **Antes/depois ao vivo** | Arraste a linha sobre o quadro para comparar o original com o tratado, em Quadro ou 100%. |
| **Análise automática** | Mede nitidez, ruído, brilho e faixa de cada vídeo, mostra o histograma e aplica as recomendações com um clique. |
| **Lote** | Ajustes para **todos os vídeos** ou **cada vídeo** separado; arraste vídeos ou uma pasta inteira. |
| **Saída para o Instagram** | Até 1080×1920, H.264 High, qualidade Leve (~8 Mbps), Equilibrada (~12 Mbps) ou Alta (~20 Mbps), 30/60 fps ou original, áudio AAC 256 kbps. |
| **Modo Avançado** | Mostra a ficha técnica do vídeo e controles extras (raio do high-pass, brilho, vibrance). |

Aceita MP4, MOV, MKV, AVI, WEBM, M4V, MTS, MXF e WMV. Tudo roda **localmente**: nenhum vídeo sai do seu computador.

## Instalação

1. Baixe `InstagramQuality-Setup-<versão>.exe` na página de [Releases](../../releases/latest).
2. Execute o instalador (não exige administrador). O FFmpeg já vai junto.
3. Os vídeos convertidos ficam em `Vídeos\Instagram Quality`.

> O Windows SmartScreen pode avisar sobre "editor desconhecido", porque o instalador não é assinado digitalmente. Clique em **Mais informações → Executar assim mesmo**.

## Como usar

1. **Adicione os vídeos**: arraste arquivos ou uma pasta para a janela, ou use **+ Vídeos** / **+ Pasta**.
2. **Ajuste a imagem**: escolha uma predefinição e refine nitidez, cor e limpeza. Arraste a linha do quadro para comparar antes e depois.
3. **Analise**: clique em **Analisar** (ou **Analisar todos**) e use **Aplicar recomendações**.
4. **Converta**: clique em **Converter** e abra a **Pasta de saída**.

Dica: o botão **Avançado** (canto superior) revela a ficha técnica e os controles extras.

## Rodar pelo código

Requisitos: Python 3.10+ no Windows e um `ffmpeg.exe` (build "full") na pasta do projeto, ou `ffmpeg` no PATH.

```bash
git clone https://github.com/muri222/instagram-quality.git
cd instagram-quality
pip install -r requirements.txt
python insta.py            # abre a janela
python insta.py video.mp4  # ou passe arquivos/pastas
```

Estrutura:

- `insta.py`: interface (Tkinter, tema escuro com acento limão).
- `engine.py`: motor (montagem dos filtros FFmpeg, codificação, analisador de vídeo).
- `fonts/`, `icon.ico`: recursos visuais.
- `instalador.iss`: script do instalador (Inno Setup 6).

### Gerar o executável e o instalador

```bash
python -m PyInstaller --onefile -w --name insta --icon "<abs>\icon.ico" --add-data "<abs>\fonts;fonts" --add-data "<abs>\icon.ico;." insta.py --distpath .
"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" instalador.iss
```

Ao mudar de versão, atualize `AppVer` em `instalador.iss` e `APP_VERSION` em `engine.py`. Use `--onefile` (o `--onedir` deixa a instalação bem mais lenta por causa do antivírus).

## Configuração e dados

- Config: `%APPDATA%\InstagramQuality\config.json`.
- Versão portátil (sem instalador): coloque `insta.exe` e `ffmpeg.exe` na mesma pasta; a saída vai para a pasta `output` ao lado.

## Licenças

O código é [MIT](LICENSE). O instalador inclui o **FFmpeg** (build "full" da gyan.dev, **GPL v3**), a fonte **Poppins** (SIL OFL 1.1) e bibliotecas permissivas (Python, Tcl/Tk, Pillow, NumPy). Detalhes em [LICENCAS.txt](LICENCAS.txt) e [ffmpeg-LICENSE.txt](ffmpeg-LICENSE.txt). Código-fonte do FFmpeg: <https://ffmpeg.org>.
