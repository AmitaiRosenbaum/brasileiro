from collections import defaultdict

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from songAPI.songs.metadata_overrides import (
    build_overrides_key,
    read_overrides,
    upsert_song_overrides,
    write_overrides,
)
from songAPI.songs.models import Artist, Song, SongMetadataOverride
from songAPI.songs.models import normalize_search_text
from songAPI.songs.views import (
    build_b2_client,
    build_manifest_key,
    get_song_storage_key,
    manifest_final_file_for_song,
    read_manifest,
    write_manifest,
)


ARTIST_ALIASES = {
    'Alcir Pires Vermelho': 'Alcyr Pires Vermelho',
    'Alfredo da Rocha Viana Filho': 'Pixinguinha',
    'Antonio Adolfo': 'Antônio Adolfo',
    'Vinicius de Moraes': 'Vinícius de Moraes',
    'Vinicius Cantuária': 'Vinícius Cantuária',
    'Ronaldo Bóscoli': 'Ronaldo Bôscoli',
    'Cristovão Bastos': 'Cristóvão Bastos',
    'Antonio Almeida': 'Antônio Almeida',
    'Antonio Cicero': 'Antônio Cícero',
    'Antônio Nassara': 'Antônio Nássara',
    'Claudio Cartier': 'Cláudio Cartier',
    'Luiz Claudio Ramos': 'Luiz Cláudio Ramos',
    'Lysias Enio': 'Lysias Ênio',
    'Lysis Enio': 'Lysias Ênio',
    'Gutemberg Guarabira': 'Gutemberg Guarabyra',
    'Haroldo Tapajos': 'Haroldo Tapajós',
    'Moacyr Santos': 'Moacir Santos',
    'Oswaldo Santiago': 'Osvaldo Santiago',
    'Paulo Tapajos': 'Paulo Tapajós',
    'Lourival Carvalho (Louro)': 'Louro',
    'Zé Gonçalves': 'José Gonçalves',
}


TITLE_GROUPS = {
    'A Banda': [1802, 305],
    'Águas de Março': [1853, 589, 871],
    'A Paz': [1808, 707],
    'Aquele Abraço': [1810, 991],
    'Atrás da Porta': [1859, 472, 533],
    'Beijo Partido': [1862, 717],
    'Chega de Saudade': [1868, 781, 877],
    'Como Dizia o Poeta': [1920, 2037],
    'Eu e a Brisa': [1827, 605],
    'Falsa Baiana': [1829, 793],
    'Gente Humilde': [1833, 492, 1984],
    'Lua Cheia': [1932, 496],
    'Manhã de Carnaval': [1884, 617],
    'Maria Vai com as Outras': [1935, 2046],
    'Minha Namorada': [1887, 566, 2104],
    'Nada Como Ter Amor': [744, 1994],
    'O Barquinho': [1841, 569],
    'O Bêbado e a Equilibrista': [1890, 1121],
    'O Cantador': [1842, 746],
    'Sabe Você': [632, 2118],
    'Sabiá': [753, 404, 918],
    'Samba da Bênção': [2063, 633],
    'Samba da Volta': [1951, 2119],
    'Samba de Verão': [1895, 695],
    'Se Todos Fossem Iguais a Você': [757, 919, 2126],
    'Tarde em Itapoã': [1957, 761, 1848, 2071],
    'Tem Dó': [2130, 583],
    'Testamento': [1958, 2121],
    'Todo o Sentimento': [1897, 410],
    'Valsinha': [358, 2133],
}


EXPLICIT_CORRECTIONS = {
    763: ('Tristeza de nós dois', 'Bebeto, Durval Ferreira, Maurício Einhorn'),
    1850: ('Tristeza de nós dois', 'Bebeto, Durval Ferreira, Maurício Einhorn'),
    482: ('Com Açúcar, com Afeto', 'Chico Buarque'),
    368: ('Assentamento', 'Chico Buarque'),
    565: ('Meditação', 'Antônio Carlos Jobim, Newton Mendonça'),
    792: ('Duas Contas', 'Garoto'),
    1086: ('Samba do Pouso', 'João Bosco, Vinícius de Moraes'),
    1811: ('As Rosas Não Falam', 'Cartola'),
    1825: ('Da Cor do Pecado', 'Bororó'),
    1881: ('Jura', 'Sinhô'),
    552: ('Hô-bá-lá-lá', 'João Gilberto'),
    351: ('Sem Açúcar', 'Chico Buarque'),
    925: ('Água de Meninos', 'Capinam, Gilberto Gil'),
    650: ('A Felicidade', 'Antônio Carlos Jobim, Vinícius de Moraes'),
    831: ('A Felicidade', 'Antônio Carlos Jobim, Vinícius de Moraes'),
    700: ('Teresa da Praia', 'Antônio Carlos Jobim, Billy Blanco'),
    867: ('Teresa da Praia', 'Antônio Carlos Jobim, Billy Blanco'),
    948: ('Extra', 'Gilberto Gil'),
    1010: ('Extra', 'Gilberto Gil'),
    538: ('Brigas Nunca Mais', 'Antônio Carlos Jobim, Vinícius de Moraes'),
    840: ('Brigas Nunca Mais', 'Antônio Carlos Jobim, Vinícius de Moraes'),
    1972: ('Brigas Nunca Mais', 'Antônio Carlos Jobim, Vinícius de Moraes'),
    555: ('Eu Sei Que Vou Te Amar', 'Antônio Carlos Jobim, Vinícius de Moraes'),
    879: ('Eu Sei Que Vou Te Amar', 'Antônio Carlos Jobim, Vinícius de Moraes'),
    835: ('Chora Coração', 'Antônio Carlos Jobim, Vinícius de Moraes'),
    1978: ('Chora Coração', 'Antônio Carlos Jobim, Vinícius de Moraes'),
    598: ('Canção do Amanhecer', 'Edu Lobo, Vinícius de Moraes'),
    2086: ('Canção do Amanhecer', 'Edu Lobo, Vinícius de Moraes'),
    458: ('Samba para Vinicius', 'Chico Buarque, Toquinho'),
    1953: ('Samba para Vinicius', 'Chico Buarque, Toquinho'),
    1034: ('Preciso Aprender a Só Ser', 'Gilberto Gil'),
    687: ('Pouca Duração', 'Pacífico Mascarenhas'),
    743: ('Mundo Velho', 'Sérgio Ricardo'),
    677: ('Maria do Maranhão', 'Carlos Lyra, Nelson Lins e Barros'),
    1903: ('A bailarina', 'Mutinho, Toquinho'),
    1904: ('A bicicleta', 'Mutinho, Toquinho'),
    1908: ('Ao que vai chegar', 'Mutinho, Toquinho'),
    1927: ('Escravo da alegria', 'Mutinho, Toquinho'),
    1943: ('O Caderno', 'Mutinho, Toquinho'),
    1911: ('Canção pra Jade', 'Mutinho, Toquinho'),
    # Production catalogue audit approved on 27 November 2026.
    692: ('Primavera', 'Carlos Lyra, Vinícius de Moraes'),
    718: ('Ê Menina', 'Gutemberg Guarabyra, João Donato'),
    720: ('Emoriô', 'Gilberto Gil, João Donato'),
    878: ('Estrada do Sol', 'Antônio Carlos Jobim, Dolores Duran'),
    898: ('Água de Beber', 'Antônio Carlos Jobim, Vinícius de Moraes'),
    907: ('Esperança Perdida', 'Antônio Carlos Jobim, Billy Blanco'),
    937: ('Clichê do Clichê', 'Gilberto Gil, Vinícius Cantuária'),
    1987: ('Lamento de um Homem Só', 'Carlos Lyra, Vinícius de Moraes'),
    1991: ('Menina das Duas Tranças', 'Toquinho, Vinícius de Moraes'),
    2014: ('Tatamirô', 'Toquinho, Vinícius de Moraes'),
    2018: ('Também Quem Mandou', 'Carlos Lyra, Vinícius de Moraes'),
    2070: ('Sem Você', 'Antônio Carlos Jobim, Vinícius de Moraes'),
    2098: ('Lamentos', 'Pixinguinha, Vinícius de Moraes'),
    2128: ('Soneto de Separação', 'Antônio Carlos Jobim, Vinícius de Moraes'),
    2967: ('Chula-ô', 'Ary Barroso'),
    3001: ('Tu qué tomá meu home', 'Ary Barroso'),
    3056: (
        'Aqueles olhos verdes (Aquellos ojos verdes)',
        'Adolfo Utrera, João de Barro, Nilo Menéndez',
    ),
    3081: (
        'Luzes da ribalta (Limelight)',
        'Antônio Almeida, Charles Chaplin, João de Barro',
    ),
    3101: (
        'Sorri (Smile)',
        'Charles Chaplin, Geoffrey Parsons, João de Barro, John Turner',
    ),
    3110: (
        'Valsa da despedida (Farewell Waltz)',
        'Alberto Ribeiro, João de Barro, Robert Burns',
    ),
    3122: ('Cartão de Visita', 'Carlos Lyra, Vinícius de Moraes'),
    3141: ('Maria do Maranhão', 'Carlos Lyra, Nelson Lins e Barros'),
    3233: (
        'Aquele bilhetinho',
        'Augusto Garcez, Nelson Cavaquinho, Wilson Canegal',
    ),
    3293: ('Balada do Esplanada', 'Cazuza, Oswald de Andrade'),
    3482: (
        'Essa nega fulô',
        'Dorival Caymmi, Jorge de Lima, Osvaldo Santiago',
    ),
    3575: ('Jobiniando', 'Ivan Lins, Martinho da Vila'),
    3599: ('Emoriô', 'Gilberto Gil, João Donato'),
    3620: ('Ê Menina', 'Gutemberg Guarabyra, João Donato'),
    3635: ('Nana das Águas', 'Geraldo Carneiro, João Donato'),
}


def normalize_artist_text(value):
    return ', '.join(
        ARTIST_ALIASES.get(name.strip(), name.strip())
        for name in value.split(',')
        if name.strip()
    )


def song_identity(title, artist_text):
    """Return an order-, case-, accent-, and punctuation-insensitive identity."""
    artists = sorted(
        normalize_search_text(name)
        for name in artist_text.split(',')
        if name.strip()
    )
    return normalize_search_text(title), tuple(artists)


def build_plan(songs):
    by_id = {song.pk: song for song in songs}
    reviewed_ids = set(EXPLICIT_CORRECTIONS)
    reviewed_ids.update(song_id for ids in TITLE_GROUPS.values() for song_id in ids)
    missing_ids = sorted(reviewed_ids - set(by_id))
    if missing_ids:
        raise CommandError(f'Reviewed production song IDs are missing: {missing_ids}')

    plan = {
        song.pk: {
            'title': song.name,
            'artist_text': normalize_artist_text(song.artist_text),
        }
        for song in songs
    }
    for title, song_ids in TITLE_GROUPS.items():
        for song_id in song_ids:
            plan[song_id]['title'] = title
    for song_id, (title, artist_text) in EXPLICIT_CORRECTIONS.items():
        plan[song_id] = {
            'title': title,
            'artist_text': normalize_artist_text(artist_text),
        }

    # Consolidate harmless display variants into one persisted song group.  A
    # majority spelling and credit order win; ties retain the values from the
    # oldest record.
    identity_groups = defaultdict(list)
    for song in songs:
        data = plan[song.pk]
        identity_groups[song_identity(data['title'], data['artist_text'])].append(song)
    for group in identity_groups.values():
        if len(group) < 2:
            continue
        title_counts = defaultdict(int)
        artist_text_counts = defaultdict(int)
        first_title_id = {}
        first_artist_text_id = {}
        for song in group:
            title = plan[song.pk]['title']
            artist_text = plan[song.pk]['artist_text']
            title_counts[title] += 1
            artist_text_counts[artist_text] += 1
            first_title_id.setdefault(title, song.pk)
            first_artist_text_id.setdefault(artist_text, song.pk)
        canonical_title = min(
            title_counts,
            key=lambda title: (-title_counts[title], first_title_id[title]),
        )
        canonical_artist_text = min(
            artist_text_counts,
            key=lambda artist_text: (
                -artist_text_counts[artist_text],
                first_artist_text_id[artist_text],
            ),
        )
        for song in group:
            plan[song.pk]['title'] = canonical_title
            plan[song.pk]['artist_text'] = canonical_artist_text

    groups = defaultdict(list)
    for song in songs:
        data = plan[song.pk]
        groups[(data['title'], data['artist_text'])].append(song)
    for group in groups.values():
        for version, song in enumerate(
            sorted(group, key=lambda item: (item.version, item.pk)),
            start=1,
        ):
            plan[song.pk]['version'] = version
    return plan


class Command(BaseCommand):
    help = 'Apply the catalogue corrections approved on 22 November 2026.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        songs = list(
            Song.objects.select_related('book').prefetch_related('artist').order_by('pk')
        )
        plan = build_plan(songs)
        changed_songs = [
            song
            for song in songs
            if song.name != plan[song.pk]['title']
            or song.artist_text != plan[song.pk]['artist_text']
            or song.version != plan[song.pk]['version']
            or {artist.name for artist in song.artist.all()}
            != {name.strip() for name in plan[song.pk]['artist_text'].split(',')}
        ]
        self.stdout.write(
            f"Planned {len(changed_songs)} changed physical scores out of {len(songs)}."
        )
        for song in changed_songs[:20]:
            data = plan[song.pk]
            self.stdout.write(
                f"  {song.pk}: {song.name} / {song.artist_text} / v{song.version}"
                f" -> {data['title']} / {data['artist_text']} / v{data['version']}"
            )
        if len(changed_songs) > 20:
            self.stdout.write(f'  ... and {len(changed_songs) - 20} more')
        if dry_run:
            self.stdout.write(self.style.SUCCESS('Dry run complete; nothing was changed.'))
            return

        client = build_b2_client()
        bucket = settings.AWS_STORAGE_BUCKET_NAME
        manifest_key = build_manifest_key()
        overrides_key = build_overrides_key(settings.B2_SONGS_PREFIX)
        fieldnames, manifest_rows = read_manifest(client, bucket, manifest_key)
        existing_overrides = read_overrides(client, bucket, overrides_key)
        manifest_by_file = {row.get('final_file'): row for row in manifest_rows}
        missing_manifest_files = sorted(
            manifest_final_file_for_song(song)
            for song in changed_songs
            if manifest_final_file_for_song(song) not in manifest_by_file
        )
        if missing_manifest_files:
            raise CommandError(
                f'Manifest is missing {len(missing_manifest_files)} changed files: '
                f'{missing_manifest_files[:10]}'
            )

        with transaction.atomic():
            for song in songs:
                song.version = 1_000_000 + song.pk
                song.save(update_fields=['version'])

            updated_overrides = existing_overrides
            for song in songs:
                data = plan[song.pk]
                song.name = data['title']
                song.artist_text = data['artist_text']
                song.version = data['version']
                song.save(update_fields=['name', 'artist_text', 'version'])

                if song not in changed_songs:
                    continue
                artists = []
                for artist_name in (
                    name.strip() for name in data['artist_text'].split(',') if name.strip()
                ):
                    artist, _created = Artist.objects.get_or_create(name=artist_name)
                    artists.append(artist)
                song.artist.set(artists)
                storage_key = get_song_storage_key(song)
                SongMetadataOverride.objects.update_or_create(
                    storage_key=storage_key,
                    defaults={
                        'song': song,
                        'book_title': song.book.title if song.book_id else '',
                        'book_song_index': song.book_song_index,
                        'title': data['title'],
                        'artist_text': data['artist_text'],
                        'version': data['version'],
                    },
                )
                row = manifest_by_file[manifest_final_file_for_song(song)]
                row['title'] = data['title']
                row['artist'] = data['artist_text']
                if 'version' in fieldnames:
                    row['version'] = str(data['version'])
                updated_overrides = upsert_song_overrides(
                    updated_overrides,
                    [song],
                    data['title'],
                    data['artist_text'],
                    {song.pk: data['version']},
                )

            write_overrides(client, bucket, overrides_key, updated_overrides)
            write_manifest(client, bucket, manifest_key, fieldnames, manifest_rows)
            Artist.objects.filter(song__isnull=True).delete()

        self.stdout.write(
            self.style.SUCCESS(
                f'Applied and persisted {len(changed_songs)} score corrections.'
            )
        )
