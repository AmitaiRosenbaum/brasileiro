from django.db import migrations


OPTIMIZED_COVERS = {
    'Ary Barroso I': 'ary-barroso-i-20261127.webp',
    'Ary Barroso II': 'ary-barroso-ii-20261127.webp',
    'As 101 Melhores Canções do Século XX I': 'as-101-melhores-i-20261127.webp',
    'As 101 Melhores Canções do Século XX II': 'as-101-melhores-ii-20261127.webp',
    'Bossa Nova I': 'bossa-nova-i-20261127.webp',
    'Bossa Nova II': 'bossa-nova-ii-20261127.webp',
    'Bossa Nova III': 'bossa-nova-iii-20261127.webp',
    'Bossa Nova IV': 'bossa-nova-iv-20261127.webp',
    'Bossa Nova V': 'bossa-nova-v-20261127.webp',
    'Braguinha': 'braguinha-20261127.webp',
    'Caetano Veloso II': 'caetano-veloso-ii-20261127.webp',
    'Carlos Lyra I': 'carlos-lyra-i-20261127.webp',
    'Cartola': 'cartola-20261127.webp',
    'Cavaquinho': 'cavaquinho-20261127.webp',
    'Cazuza I': 'cazuza-i-20261127.webp',
    'Chico Buarque I': 'chico-buarque-i-20261127.webp',
    'Chico Buarque II': 'chico-buarque-ii-20261127.webp',
    'Chico Buarque III': 'chico-buarque-iii-20261127.webp',
    'Chico Buarque IV': 'chico-buarque-iv-20261127.webp',
    'Choro II': 'choro-ii-20261127.webp',
    'Djavan I': 'djavan-i-20261127.webp',
    'Djavan II': 'djavan-ii-20261127.webp',
    'Dorival Caymmi I': 'dorival-caymmi-i-20261127.webp',
    'Dorival Caymmi II': 'dorival-caymmi-ii-20261127.webp',
    'Gilberto Gil I': 'gilberto-gil-i-20261127.webp',
    'Gilberto Gil II': 'gilberto-gil-ii-20261127.webp',
    'Ivan Lins I': 'ivan-lins-i-20261127.webp',
    'Ivan Lins II': 'ivan-lins-ii-20261127.webp',
    'Joao Bosco I': 'joao-bosco-i-20261127.webp',
    'Joao Bosco II': 'joao-bosco-ii-20261127.webp',
    'Joao Bosco III': 'joao-bosco-iii-20261127.webp',
    'João Donato': 'joao-donato-20261127.webp',
    'Luiz Gonzaga I': 'luiz-gonzaga-i-20261127.webp',
    'Noel Rosa II': 'noel-rosa-ii-20261127.webp',
    'Noel Rosa III': 'noel-rosa-iii-20261127.webp',
    'Tom Jobim I': 'tom-jobim-i-20261127.webp',
    'Tom Jobim II': 'tom-jobim-ii-20261127.webp',
    'Tom Jobim III': 'tom-jobim-iii-20261127.webp',
    'Toquinho': 'toquinho-20261127.webp',
    'Vinicius de Moraes I': 'vinicius-de-moraes-i-20261127.webp',
    'Vinicius de Moraes II': 'vinicius-de-moraes-ii-20261127.webp',
    'Vinicius de Moraes III': 'vinicius-de-moraes-iii-20261127.webp',
}

PREVIOUS_COVERS = {
    'Bossa Nova I': 'book-covers/Bossa_I.jpg',
    'Bossa Nova II': 'book-covers/Bossa_II.jpg',
    'Bossa Nova III': 'book-covers/Bossa_III.jpg',
    'Bossa Nova IV': 'book-covers/Bossa_IV.jpg',
    'Bossa Nova V': 'book-covers/bossa_5.jpg',
    'Chico Buarque I': 'book-covers/Chico_1.webp',
    'Chico Buarque II': 'book-covers/chico_2.jpg',
    'Chico Buarque III': 'book-covers/chico_3.jpg',
    'Chico Buarque IV': 'book-covers/chico_4.jpg',
    'Gilberto Gil I': 'book-covers/gil_1.jpg',
    'Gilberto Gil II': 'book-covers/gil_2.jpg',
    'Joao Bosco I': 'book-covers/bosco_1.jpg',
    'Joao Bosco II': 'book-covers/Bosco_2.jpg',
    'Joao Bosco III': 'book-covers/Bosco_3.webp',
    'Tom Jobim I': 'book-covers/jobim_1.jpg',
    'Tom Jobim II': 'book-covers/Jobim_2.jpg',
    'Tom Jobim III': 'book-covers/Jobim_III.jpg',
}


def install_optimized_covers(apps, schema_editor):
    Book = apps.get_model('songs', 'Book')
    for title, filename in OPTIMIZED_COVERS.items():
        Book.objects.filter(title=title).update(
            cover_image=f'book-covers/optimized/{filename}',
        )


def restore_previous_covers(apps, schema_editor):
    Book = apps.get_model('songs', 'Book')
    for title in OPTIMIZED_COVERS:
        Book.objects.filter(title=title).update(
            cover_image=PREVIOUS_COVERS.get(title, ''),
        )


class Migration(migrations.Migration):
    dependencies = [('songs', '0011_songmetadataoverride')]

    operations = [
        migrations.RunPython(install_optimized_covers, restore_previous_covers),
    ]
