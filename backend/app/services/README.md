# Services

images.py validates uploaded content with Pillow, strips metadata by re-encoding, and generates JPEG + SHA-256.
Lifecycle and authorization are implemented in api/router.py and core/security.py.
