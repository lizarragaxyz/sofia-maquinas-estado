"""Ciclo de vida de un comando de SOFIA como maquina de estados.

TRANSICIONES dice, para cada (estado, evento), cual es el siguiente estado.
Un evento que no esta en la tabla no cambia el estado: se ignora.
"""

TRANSICIONES = {
    ('RECIBIDO', 'crc_ok'): 'VALIDADO',
    ('RECIBIDO', 'crc_error'): 'DESCARTADO',
    ('VALIDADO', 'ejecutar'): 'EJECUTANDO',
    ('EJECUTANDO', 'en_posicion'): 'COMPLETADO',
}


def siguiente(estado, evento):
    return TRANSICIONES.get((estado, evento), estado)


estado = 'RECIBIDO'
eventos = ['crc_ok', 'crc_error', 'ejecutar', 'en_posicion']

for evento in eventos:
    nuevo = siguiente(estado, evento)
    print(f'{estado:<10} --{evento}--> {nuevo}')
    estado = nuevo
