"""Main project modules"""

from flask import request,session
from werkzeug.utils import secure_filename
from .app import app
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from PIL import Image, UnidentifiedImageError
from stegano import lsb
import base64
import hashlib
import os,random

class TextEncryption():
    
    def __init__(self):
        data = request.get_json() 
        self.key = Utils.return_key(data["key"],data["key_type"])
        self.value = data["value"]
    
    def encrypt(self):
        """Encrypt Text"""

        if not self.value == '':
            try:
                fernet = Fernet(self.key)
                plaintext = self.value.encode()
                encryptedtext = fernet.encrypt(plaintext)
                return {"status":"1","value":encryptedtext.decode()}
            except:
                return {"status":"0","value":"Encryption failed! , possible problem: key not found or invalid key"}
        else:
            return {"status":"0","value":"Encryption failed! , No text to encrypt, please type something"}
    
    def decrypt(self):
        """Decrypt Text"""

        if not self.value == '':
           try:
               fernet = Fernet(self.key)
               plaintext = self.value.encode()
               decryptedtext = fernet.decrypt(plaintext)
               # Decrypt text until get an unencrypted text ( useful when the text is encrypted multiple times )
               while True:
                   try:
                       decryptedtext = fernet.decrypt(decryptedtext)
                   except:
                       return {"status":"1","value":decryptedtext.decode()}
           except:
               return {"status":"0","value":"Decryption failed! , possible problem: key not found or invalid key"}
        else:
            return {"status":"0","value":"Decryption failed! , No text to decrypt, please type something"}       

class FileEncryption():
    
    def __init__(self):
        data = request.form 
        self.key = Utils.return_key(data["key"],data["key_type"])
        self.path = session.get('path','not set')
        self.filename = session.get('filename','not set')
    
    def encrypt(self):
        """Encrypt uploaded file"""

        fernet = Fernet(self.key)
        with open(os.path.join(self.path,self.filename) , 'rb') as f:
            data = f.read()
        encryptedfile = fernet.encrypt(data)
        with open(os.path.join(self.path,self.filename),'wb') as f:
            f.write(encryptedfile)
        return self.filename

    def decrypt(self):
        """Decrypt uploaded file"""
        
        #key = request.form["key"]
        fernet = Fernet(self.key)
        with open(os.path.join(self.path,self.filename) , 'rb') as f:
            data = f.read()
        decryptedfile = fernet.decrypt(data)
        with open(os.path.join(self.path,self.filename),'wb') as f:
            f.write(decryptedfile)
        return self.filename    


class ImageSteganography():
    """Hide and extract encrypted text payloads in PNG images"""

    MAGIC = "ENCIPHERR_STEGO"
    VERSION = "1"
    CLEANUP_MARGIN_BYTES = 32
    MAX_IMAGE_PIXELS = 25_000_000

    def __init__(self):
        data = request.form
        self.key = Utils.return_key(data.get("key", ""), data.get("key_type", ""))
        self.value = data.get("txt", "")
        self.uploaded_file = request.files.get("stego_file")
        self.path = session.get('path','not set')
        self.filename = session.get('filename','not set')

    def hide(self):
        """Hide encrypted text in a PNG image and return the output filename"""

        self._validate_text_payload()
        self._validate_key()
        input_path, output_path, output_filename = self._prepare_png_upload()

        try:
            with Image.open(input_path) as image:
                self._validate_png(image)
                payload = self._build_payload()
                self._validate_capacity(image, payload)

            stego_image = lsb.hide(input_path, payload)
            stego_image.save(output_path)
            session["path"] = self.path
            session["filename"] = output_filename
            return output_filename
        except UnidentifiedImageError:
            self._cleanup_directory(self.path)
            raise ValueError("Invalid PNG image")
        except Exception:
            self._cleanup_directory(self.path)
            raise

    def extract(self):
        """Extract and decrypt a hidden payload from a PNG image"""

        self._validate_key()
        input_path = self._prepare_png_upload_for_extract()

        try:
            with Image.open(input_path) as image:
                self._validate_png(image)

            revealed_payload = lsb.reveal(input_path)
            if not revealed_payload:
                raise ValueError("No hidden payload found in this PNG image")

            plaintext = self._decode_payload(revealed_payload)
            return plaintext
        except UnidentifiedImageError:
            raise ValueError("Invalid PNG image")
        finally:
            self._cleanup_directory(self.path)
            session["path"] = ""
            session["filename"] = ""

    def _validate_key(self):
        if self.key == "":
            raise ValueError("key not found or invalid key")

    def _validate_text_payload(self):
        if self.value == "":
            raise ValueError("No text to hide, please type something")

    def _prepare_png_upload(self):
        if self.uploaded_file is None or self.uploaded_file.filename == "":
            raise ValueError("no image to upload")

        if not self._is_png_filename(self.uploaded_file.filename):
            raise ValueError("Only PNG images are supported")

        user_name = session.get('username','not set')
        parent_dir = app.config["UPLOAD_FOLDER"]
        self.path = os.path.join(parent_dir, user_name)
        os.mkdir(self.path)

        self.filename = secure_filename(self.uploaded_file.filename)
        input_path = os.path.join(self.path, self.filename)
        self.uploaded_file.save(input_path)
        output_filename = f"stego_{os.path.splitext(self.filename)[0]}.png"
        output_path = os.path.join(self.path, output_filename)
        return input_path, output_path, output_filename

    def _prepare_png_upload_for_extract(self):
        if self.uploaded_file is None or self.uploaded_file.filename == "":
            raise ValueError("no image to upload")

        if not self._is_png_filename(self.uploaded_file.filename):
            raise ValueError("Only PNG images are supported")

        user_name = session.get('username','not set')
        parent_dir = app.config["UPLOAD_FOLDER"]
        self.path = os.path.join(parent_dir, user_name)
        os.mkdir(self.path)

        self.filename = secure_filename(self.uploaded_file.filename)
        input_path = os.path.join(self.path, self.filename)
        self.uploaded_file.save(input_path)
        return input_path

    def _build_payload(self):
        fernet = Fernet(self.key)
        ciphertext = fernet.encrypt(self.value.encode()).decode()
        checksum = hashlib.sha256(ciphertext.encode()).hexdigest()
        return f"{self.MAGIC}|{self.VERSION}|{checksum}|{ciphertext}"

    def _decode_payload(self, payload):
        try:
            magic, version, checksum, ciphertext = payload.split("|", 3)
        except ValueError:
            raise ValueError("Invalid or corrupted stego image")

        if magic != self.MAGIC or version != self.VERSION:
            raise ValueError("Invalid or corrupted stego image")

        if hashlib.sha256(ciphertext.encode()).hexdigest() != checksum:
            raise ValueError("Invalid or corrupted stego image")

        try:
            fernet = Fernet(self.key)
            return fernet.decrypt(ciphertext.encode()).decode()
        except Exception:
            raise ValueError("Decryption failed! , possible problem: key not found or invalid key")

    def _validate_capacity(self, image, payload):
        width, height = image.size
        max_bytes = max(0, ((width * height * 3) // 8) - self.CLEANUP_MARGIN_BYTES)
        payload_size = len(payload.encode())

        if payload_size > max_bytes:
            raise ValueError("Payload too large for the selected image")

    def _validate_png(self, image):
        if image.format != "PNG":
            raise ValueError("Only PNG images are supported")
        if image.mode not in ("RGB", "RGBA"):
            raise ValueError("PNG must use RGB or RGBA color mode")
        if image.width * image.height > self.MAX_IMAGE_PIXELS:
            raise ValueError("Image is too large to process safely")

    def _is_png_filename(self, filename):
        return os.path.splitext(filename)[1].lower() == ".png"

    def _cleanup_directory(self, path):
        if path and path != "not set" and os.path.exists(path):
            import shutil
            shutil.rmtree(path)


class Utils():
    
    def return_key(key,type):
        """generate key from custom pwd if key_type == pwd else return the AES key"""

        if type == "pwd":
            if key == "":return ""
            salt = app.config["SALT"]
            kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=390000,)
            key = base64.urlsafe_b64encode(kdf.derive(key.encode()))
            return key
        else:
            return key    
    
    def genkey():
        """Generate random key"""
        key = Fernet.generate_key()
        return key.decode()
    
    def SetupGuestSession():
        """Setup a guest session when an user enters the website, only for file upload"""
        
        import string
        user_name = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))
        session["username"] = user_name
        session["path"] = ""
        session["filename"] = ""
    
    def Upload_file():
        """Upload the file from the client to ther server"""
    
        key_value = request.form.get("key", "")
        uploaded_file = request.files.get("file")

        if key_value != "":
            if uploaded_file is None or uploaded_file.filename == "":
                raise ValueError("no file to upload")

            user_name = session.get('username','not set')
            parent_dir = app.config["UPLOAD_FOLDER"] # set path
            path = os.path.join(parent_dir, user_name) # temporary folder with same name as guest username
            os.mkdir(path) #create temp dir
            
            uploaded_file.save(os.path.join(path,secure_filename(uploaded_file.filename))) # save file to the temp dir
            filename = secure_filename(uploaded_file.filename) # get filename
            session["path"]=path 
            session["filename"]=filename
        else:
            raise ValueError("key not found") # no key specified - raise error - the file will be deleted.         




