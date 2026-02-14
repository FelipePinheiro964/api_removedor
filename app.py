from flask import Flask, request, send_file, jsonify
from rembg import remove, new_session
from io import BytesIO
from PIL import Image
import zipfile
import os

app = Flask(__name__)

# --- O SEGREDO DO MODO LITE ---
# Carregamos a "Sessão" globalmente com o modelo 'u2netp' (Leve/Mobile)
# Isso faz o download ser rapido (4MB vs 176MB) e usa pouca RAM.
model_name = "u2netp"
session = new_session(model_name)

def processar_imagem(image_bytes, bg_color=None):
    input_image = Image.open(BytesIO(image_bytes)).convert("RGBA")
    
    # Passamos a session aqui para usar o modelo leve
    output_image = remove(input_image, session=session)
    
    extension = '.png'
    mimetype = 'image/png'
    format_img = 'PNG'

    if bg_color and bg_color.lower() != 'transparent':
        try:
            new_bg = Image.new("RGBA", output_image.size, bg_color)
            new_bg.paste(output_image, (0, 0), output_image)
            output_image = new_bg.convert("RGB")
            extension = '.jpg'
            mimetype = 'image/jpeg'
            format_img = 'JPEG'
        except Exception as e:
            print(f"Erro na cor {bg_color}: {e}")

    img_io = BytesIO()
    output_image.save(img_io, format_img)
    img_io.seek(0)
    return img_io, mimetype, extension

@app.route('/remove-bg', methods=['POST'])
def remove_background():
    if 'image' not in request.files:
        return jsonify({"error": "Envie um arquivo no campo 'image'"}), 400
    
    file = request.files['image']
    bg_color = request.form.get('color')
    filename = file.filename
    
    # --- MODO 1: ZIP ---
    if filename.lower().endswith('.zip'):
        try:
            input_zip = zipfile.ZipFile(file)
            output_zip_io = BytesIO()
            
            with zipfile.ZipFile(output_zip_io, 'w', zipfile.ZIP_DEFLATED) as output_zip:
                for nome_arq in input_zip.namelist():
                    if nome_arq.startswith('__') or nome_arq.endswith('/'):
                        continue
                    
                    with input_zip.open(nome_arq) as img_entry:
                        try:
                            img_io, _, ext = processar_imagem(img_entry.read(), bg_color)
                            novo_nome = os.path.splitext(nome_arq)[0] + "_no_bg" + ext
                            output_zip.writestr(novo_nome, img_io.getvalue())
                        except Exception as e:
                            print(f"Erro no ZIP: {e}")

            output_zip_io.seek(0)
            return send_file(output_zip_io, mimetype='application/zip', as_attachment=True, download_name=f"processed_{filename}")

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # --- MODO 2: UNICO ---
    else:
        try:
            img_io, mimetype, ext = processar_imagem(file.read(), bg_color)
            novo_nome = os.path.splitext(filename)[0] + "_processed" + ext
            return send_file(img_io, mimetype=mimetype, as_attachment=True, download_name=novo_nome)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)