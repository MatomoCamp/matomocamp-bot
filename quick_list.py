from data import talks
from urls import chat_rooms

for talk in talks:
    if talk.year != 2023:
        continue
    if talk.id in chat_rooms:
        continue
    print(f'    "{talk.id}": "{talk.title}",')
