import ecdsa
import hashlib
from secret_manager.gcp_secret_manager import access_secret

def sign(payload, project):

    ## Fetch secret from GCP's Secret Manager
    API_SIGNER_CLIENT_KEYPAIR = 'PRIVATE_KEY_FILE'
    pem_content = access_secret(project, API_SIGNER_CLIENT_KEYPAIR, 'latest') # CHANGE

    # Signs the payload
    signing_key = ecdsa.SigningKey.from_pem(pem_content)

    signature = signing_key.sign(
        data=payload.encode(), hashfunc=hashlib.sha256, sigencode=ecdsa.util.sigencode_der
    )

    return signature