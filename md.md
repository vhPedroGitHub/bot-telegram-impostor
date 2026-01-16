quiero hacer un bot de telegram que haga lo siguiente:
el objetivo del bot es administrar un grupo de telegram para jugar al impostor, el juego donde x cantidad de personas son impostores y la otra x cantidad son ciudadanos. los impostores no conocen la palabra y los ciudadanos si la conocen, en cada ronda cada persona dice una palabra y al final de la ronda se dice quien es un impostor si es descubiero termina la ronda, sino se continua hasta la ultima ronda y asi.

para el juego en telegram debes tener las siguientes caracteristicas. 
comandos:
/start: inicia el bot para empezar un juego.
aqui el bot hace una encuesta donde pregunta a los jugadores si quieren jugar, los jugadores solo marcan la opcion del si, los que no la marquen seran descartado para esta ronda. esta encuesta dura 3 minutos o hasta que el admin le de siguiente para pasar al juego.
cuando de siguiente el admin definira las reglas:
- el numero de impostores que no exceda claramente el numero de ciudadanos
- la cantidad de rondas siendo posibles un maximo de 5 y un minimo de 2

haz una lista exhaustiva de palabras para elegir una aleatoria. no se si haya un api gratuita para obtener palabras aleatorias segun una categoria.

a cada jugador le envias la palabra al privado y a los impostores le envias el mensaje IMPOSTOR AHORA !!!!

despues de 10 segundo y que cada jugador sepa su rol, entonces empiezas por un orden, donde le indiques a cada jugador que diga una palabra, en ese turno solo puede escribir esa persona y cuando escriba automaticamente pasa para la otra persona. al final de la ronda todos los jugadores podran escribir para discutir quien es el impostor y despues de 2 minutos o que el admin ponga el comando /end-meet sale una encuesta donde cada jugador debera votar por el impostor, esta encuesta debe durar 1 minuto o hasta que el admin le de siguiente, sino es el impostor entonces se pasa ha la siguiente ronda. si alguien en una ronda dice la palabra que era entonces termina la ronda y ganan los impostores, sino dicen la palabra y terminan las rondas y el impostor no es descubierto gana el impostor.

el admin del grupo o los admin son los unicos que pueden escribir los comandos.

hazme el bot con python y una guia para el despliegue y como usarlo