""" App Routing """

from flask import request,render_template,url_for,redirect,send_from_directory,abort,after_this_request,session
from .app import app
from src.modules import TextEncryption,FileEncryption,ImageSteganography,Utils
import os,shutil


def clear_download_session(path, filename):
    """Remove a generated download file and its temp directory safely."""

    if not path or path == 'not set' or not os.path.exists(path):
        return

    file_path = os.path.join(path, filename)

    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        if app.config["ENV"] == "DEV":
            shutil.rmtree(path, ignore_errors=True)
        else:
            try:
                os.rmdir(path)
            except OSError:
                pass
    except PermissionError:
        pass

@app.route('/genkey',methods=['GET'])
def genkey():
    return Utils.genkey()

@app.route('/text',methods=['POST'])
def text_mode():
    data = request.get_json() 

    text = TextEncryption()
    
    if data["submit_b"] == "Encrypt Text":
        response = text.encrypt()
        return response
    else:
        response = text.decrypt()
        return response 


@app.route('/',methods=['GET'])
def base():
    return redirect(url_for('home'))

@app.route('/home',methods=['POST','GET'])
def home():
    """Handle all incoming post/get requests"""
    
    if request.method == 'POST':
        Utils.SetupGuestSession()
        submit_action = request.form.get("submit_b")
        key_value = request.form.get("key", "")

        if submit_action == "Upload and Encrypt":
            try:
                Utils.Upload_file()
                try:
                    file = FileEncryption()
                    filename=file.encrypt()
                except Exception:
                    path = session.get('path','not set')
                    if path and os.path.exists(path):
                        shutil.rmtree(path)
                    return render_template('home.html', key=key_value, error_message='Encryption failed! , possible problem: key not found or invalid key')
                
                return redirect(url_for('getfile',file_name=filename))
            except Exception:
                return render_template('home.html', key=key_value, error_message='Upload failed! , possible problem: no file to upload or key not found')

        elif submit_action == "Upload and Decrypt":
            try:
                Utils.Upload_file()
                
                try:
                    file = FileEncryption()
                    filename=file.decrypt()
                except Exception:
                    path = session.get('path','not set') 
                    if path and os.path.exists(path):
                        shutil.rmtree(path)
                    return render_template('home.html', key=key_value, error_message='Decryption failed! , possible problem: key not found or invalid key')
                
                return redirect(url_for('getfile',file_name=filename))
            
            except Exception:
                return render_template('home.html', key=key_value, error_message='Upload failed! , possible problem: no file to upload or key not found')
        else:
            return render_template('home.html', key=key_value)

    else:
        return render_template('home.html')

@app.route("/get-file/<file_name>")
def getfile(file_name):
    """Return file for downloading,after download it will be deleted with the directory"""
    path = session.get('path','not set')
    #print(path)
    filename = session.get('filename','not set')
    try:
        @after_this_request
        def remove_file_and_dir(response):
            session.pop('path', None)
            session.pop('filename', None)
            response.call_on_close(lambda: clear_download_session(path, filename))
            
            return response

        return send_from_directory(directory=path, path=file_name,as_attachment=True,max_age=0)
    except FileNotFoundError:
        abort(404)

@app.route('/sw.js',methods=["GET","POST"])
def service_worker():
    from flask import make_response
    response = make_response(send_from_directory('.',path='sw.js'))
    response.headers['Content-Type'] = 'application/javascript'
    response.headers['Service-Worker-Allowed'] = '/'
    return response

@app.route('/robots.txt',methods=["GET"])
def robots_file():
    from flask import make_response
    response = make_response(send_from_directory('.',path='robots.txt'))
    response.headers["Content-type"] = "text/plain"
    return response
    
@app.route("/about")
def about():
    return render_template('about.html')

@app.route("/privacy")
def privacy():
    return render_template('privacy.html')

@app.route('/steganography',methods=['POST','GET'])
def steganography():
    """Handle PNG steganography encode and extract requests"""

    if request.method == 'POST':
        Utils.SetupGuestSession()
        submit_action = request.form.get("submit_b")
        key_value = request.form.get("key", "")
        text_value = request.form.get("txt", "")

        if submit_action == "Hide in Image":
            try:
                stego = ImageSteganography()
                filename = stego.hide()
                return redirect(url_for('getfile',file_name=filename))
            except Exception as error:
                path = session.get('path','not set')
                if path and os.path.exists(path):
                    shutil.rmtree(path)
                return render_template('steganography.html', key=key_value, value=text_value, error_message=str(error))

        if submit_action == "Extract from Image":
            try:
                stego = ImageSteganography()
                recovered_text = stego.extract()
                return render_template('steganography.html', key=key_value, value=recovered_text, success_message='Hidden message extracted successfully')
            except Exception as error:
                return render_template('steganography.html', key=key_value, value=text_value, error_message=str(error))

        return render_template('steganography.html', key=key_value, value=text_value)

    return render_template('steganography.html')

@app.errorhandler(404)
def page_not_found(error):
    return render_template("page-404.html"), 404

@app.errorhandler(500)
def server_error(error):
    return render_template("page-500.html"), 500
