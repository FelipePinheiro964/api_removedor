from flask import Flask, request, send_file, jsonify
from rembg import remove
from io import BytesIO
from PIL import Image
import zipfile
import os

app = Flask(__name__)

def processar_imagem(image_bytes, bg_color=None):
    """Função auxiliar que trata uma única imagem"""
    input_image = Image.open(BytesIO(image_bytes)).convert("RGBA")
    output_image = remove(input_image)
    
    extension = '.png'
    mimetype = 'image/png'
    format_img = 'PNG'

    # Se pediu cor de fundo, aplica
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
    
    print(f"📥 Recebido: {filename} | Cor: {bg_color}")

    # --- MODO 1: PROCESSAMENTO DE ZIP (LOTE) ---
    if filename.lower().endswith('.zip'):
        try:
            # Lê o ZIP recebido
            input_zip = zipfile.ZipFile(file)
            output_zip_io = BytesIO()
            
            # Cria um novo ZIP para resposta
            with zipfile.ZipFile(output_zip_io, 'w', zipfile.ZIP_DEFLATED) as output_zip:
                for nome_arq in input_zip.namelist():
                    # Ignora pastas ou arquivos ocultos (__MACOSX)
                    if nome_arq.startswith('__') or nome_arq.endswith('/'):
                        continue
                    
                    # Processa cada imagem dentro do ZIP
                    with input_zip.open(nome_arq) as img_entry:
                        img_data = img_entry.read()
                        try:
                            # Chama nossa função de processamento
                            img_io, _, ext = processar_imagem(img_data, bg_color)
                            
                            # Define novo nome (ex: sapato.jpg -> sapato_no_bg.png)
                            novo_nome = os.path.splitext(nome_arq)[0] + "_no_bg" + ext
                            output_zip.writestr(novo_nome, img_io.getvalue())
                            print(f"   ✅ Processado no ZIP: {novo_nome}")
                        except Exception as e:
                            print(f"   ❌ Erro ao processar {nome_arq}: {e}")

            output_zip_io.seek(0)
            return send_file(
                output_zip_io, 
                mimetype='application/zip', 
                as_attachment=True, 
                download_name=f"processed_{filename}"
            )

        except Exception as e:
            return jsonify({"error": f"Erro no ZIP: {str(e)}"}), 500

    # --- MODO 2: PROCESSAMENTO ÚNICO (FOTO SOZINHA) ---
    else:
        try:
            img_io, mimetype, ext = processar_imagem(file.read(), bg_color)
            
            # Retorna o nome original no cabeçalho para o cliente saber
            novo_nome = os.path.splitext(filename)[0] + "_processed" + ext
            
            return send_file(
                img_io, 
                mimetype=mimetype,
                as_attachment=True, 
                download_name=f"processed_{filename}"  # <--- ISSO AQUI QUE MANDA O NOME
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)