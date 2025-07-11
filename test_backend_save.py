import requests
import os

def main():
    url = 'http://localhost:8000'
    token = requests.post(f'{url}/api/login', json={'username': 'admin', 'password': 'whispad'}).json()['token']
    resp = requests.post(f'{url}/api/save-note',
                         headers={'Authorization': token, 'Content-Type': 'application/json'},
                         json={'title': 'Test from python', 'content': 'Hello world'})
    print(resp.json())
    # check file exists
    folder = os.path.join('saved_notes', 'admin')
    files = os.listdir(folder)
    print('files in folder:', files)

if __name__ == '__main__':
    main()
