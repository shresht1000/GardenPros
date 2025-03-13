import keyring

service = "MyApp"
username = "myuser"
password = "krun zgdz tmuj cngd"

keyring.set_password(service, username, password)
print("Password saved securely!")
