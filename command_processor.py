import spacy
from spacy.matcher import Matcher
from typing import Dict, Any


class SpotifyCommandProcessor:
    def __init__(self):
        self.play_commands = ['reproduce', 'pon', 'escuchar']
        self.nlp = spacy.load("es_core_news_sm")
        self.matcher = Matcher(self.nlp.vocab)

        # Define patterns
        self.setup_patterns()

    def setup_patterns(self):
        # Reproducir artista patterns
        self.matcher.add("PLAY_ARTIST", [
            [{"LOWER": "reproduce"}, {"LOWER": "canciones"}, {"LOWER": "de"}, {"POS": "PROPN", "OP": "+"}],
            [{"LOWER": "pon"}, {"LOWER": "música"}, {"LOWER": "de"}, {"POS": "PROPN", "OP": "+"}],
            [{"LOWER": "escuchar"}, {"LOWER": "a"}, {"POS": "PROPN", "OP": "+"}]
        ])

        # Reproducir canción patterns
        self.matcher.add("PLAY_SONG", [
            [{"LOWER": "reproduce"}, {"TEXT": {"NOT_IN": ["canciones", "música"]}}, {"LOWER": "de"},
             {"POS": "PROPN", "OP": "+"}],
            [{"LOWER": "pon"}, {"TEXT": {"NOT_IN": ["canciones", "música"]}}, {"LOWER": "de"},
             {"POS": "PROPN", "OP": "+"}]
        ])

        # Add to playlist patterns
        self.matcher.add("ADD_TO_PLAYLIST", [
            [{"LOWER": "agregar"}, {"LOWER": "a"}, {"LOWER": "la"}, {"LOWER": "playlist"}, {"POS": "PROPN", "OP": "+"}],
            [{"LOWER": "guardar"}, {"LOWER": "en"}, {"LOWER": "la"}, {"LOWER": "playlist"}, {"POS": "PROPN", "OP": "+"}]
        ])

    def extract_song_and_artist(self, command: str) -> Dict[str, str]:
        # Keep original case for song/artist names
        command_original = command
        command_lower = command.lower()

        # Expanded command triggers
        play_indicators = [
            'reproduce', 'pon', 'escuchar',
            'reproducir', 'poner', 'tocar'
        ]

        # Find which play command was used
        used_command = None
        command_start = -1
        for indicator in play_indicators:
            if indicator in command_lower:
                used_command = indicator
                command_start = command_lower.find(indicator)
                break

        if used_command and ' de ' in command_original:
            # Extract content after the command
            content = command_original[command_start + len(used_command):].strip()

            # Split by 'de' and clean up
            parts = content.split(' de ', 1)

            if len(parts) == 2:
                song = parts[0].strip()
                artist = parts[1].strip()

                # Clean up common speech recognition artifacts
                song = self.clean_song_name(song)
                artist = self.clean_artist_name(artist)

                return {'song': song, 'artist': artist}

        return None

    def clean_song_name(self, song: str) -> str:
        """
        Clean up common speech recognition artifacts in song names
        """
        # Remove common articles that might be added
        song = song.strip()
        prefixes_to_remove = ['la canción ', 'el tema ', 'la música ']
        for prefix in prefixes_to_remove:
            if song.lower().startswith(prefix):
                song = song[len(prefix):].strip()

        # Join split words that are likely part of a title
        # Example: "keep up de o de tari" -> "keep up de odetari"
        parts = song.split()
        i = 0
        while i < len(parts) - 2:
            if parts[i + 1].lower() == 'de' and len(parts[i + 2]) <= 2:
                # Join this sequence
                parts[i:i + 3] = [''.join(parts[i:i + 3])]
            i += 1

        return ' '.join(parts)

    def clean_artist_name(self, artist: str) -> str:
        """
        Clean up common speech recognition artifacts in artist names
        """
        # Remove common prefixes
        artist = artist.strip()
        prefixes_to_remove = ['el artista ', 'la artista ', 'el cantante ', 'la cantante ']
        for prefix in prefixes_to_remove:
            if artist.lower().startswith(prefix):
                artist = artist[len(prefix):].strip()

        return artist

    def process_command(self, command: str) -> Dict[str, Any]:
        doc = self.nlp(command)
        matches = self.matcher(doc)

        print(command)

        if not matches:
            return self.process_basic_command(command)

        song_artist = self.extract_song_and_artist(command)
        if song_artist:
            # Clean up the extracted names
            song = song_artist['song']
            artist = song_artist['artist']

            return {
                'action': 'play_song',
                'song': song,
                'artist': artist,
                'message': f"Buscando {song} de {artist}"
            }

        return {"action": "unknown", "message": "No entendí el comando"}

    def process_basic_command(self, command: str) -> Dict[str, Any]:
        command = command.lower()
        if "pausa" in command or "detener" in command:
            return {"action": "pause", "message": "Pausando..."}
        elif "reproducir" in command or "continuar" in command:
            return {"action": "resume", "message": "Continuando..."}
        elif "siguiente" in command or "saltar" in command:
            return {"action": "next", "message": "Siguiente canción"}
        elif "anterior" in command or "atrás" in command:
            return {"action": "previous", "message": "Canción anterior"}
        elif "subir volumen" in command:
            return {"action": "volume_up", "message": "Subiendo volumen"}
        elif "bajar volumen" in command:
            return {"action": "volume_down", "message": "Bajando volumen"}

        return {"action": "unknown", "message": "No entendí el comando"}
