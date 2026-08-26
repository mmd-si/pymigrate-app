from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.schemas.response import InventoryDetails

valuables = [
    'anillo',
    'arete',
    'collar',
    'dije',
    'esclava',
    'gargantilla',
    'hebilla',
    'juego',
    'llavero',
    'mancuerna',
    'moneda',
    'peineta',
    'pisa corbata',
    'placa',
    'prendedor',
    'pulsera',
]

tools = ['herramienta', 'taladr', 'esmeri', 'router', 'rotomart', 'solda', 'pulid']

electronics = [
    'celular',
    'tv',
    'televisor',
    'laptop',
    'computador',
    'consola',
    'playstation',
    'xbox',
    'nintendo',
    'electrodomestico',
]


def procedural_resolver(row: 'InventoryDetails') -> str:
    segments = []

    description = (row.description or '').lower()
    pawn_type = (row.pawn_type or '').lower()
    carat_rating = row.carat_rating

    oro = 'Oro'
    plata = 'Plata'
    relojes_usados = 'Relojes Usados'
    articulos_usados = 'Artículos Usados'
    herramientas = 'Herramientas'
    electronicos = 'Electrónicos'
    varios = 'Varios'

    segments.append(
        oro
        if pawn_type == 'oro'
        else (
            plata
            if pawn_type == 'plata'
            else relojes_usados if 'reloj' in description else articulos_usados
        )
    )

    if segments[0] in [oro, plata]:
        if segments[0] == oro and 'brill' in description:
            segments.append('Brillante')

        if carat_rating:
            segments.append(carat_rating.replace('.', ''))

        for pattern in valuables:
            if pattern in description:
                segments.append(pattern.title())
                break
        else:
            segments.append(varios)

    elif segments[0] == relojes_usados:
        segments.append('Reloj')

    elif segments[0] == articulos_usados:
        for pattern in tools:
            if pattern in description:
                segments.append(herramientas)
                break
        else:
            for pattern in electronics:
                if pattern in description:
                    segments.append(electronicos)
                    break
            else:
                segments.append(varios)

    return ' / '.join(segments)
