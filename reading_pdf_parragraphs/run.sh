#!/bin/bash

# Script para ejecutar reading-pdf-paragraphs con Docker
# Uso: ./run.sh [build|start|stop|restart|test|logs]

set -e

IMAGE_NAME="reading-pdf-paragraphs"
CONTAINER_NAME="reading-pdf-paragraphs-container"
PORT=9000

# Función para mostrar ayuda
show_help() {
    echo "Uso: ./run.sh [comando]"
    echo ""
    echo "Comandos disponibles:"
    echo "  build     - Construir la imagen Docker"
    echo "  start     - Iniciar el contenedor (construye si es necesario)"
    echo "  stop      - Detener el contenedor"
    echo "  restart   - Reiniciar el contenedor"
    echo "  test      - Ejecutar una prueba con payload.json"
    echo "  logs      - Ver logs del contenedor"
    echo "  status    - Ver estado del contenedor"
    echo "  clean     - Detener y eliminar el contenedor"
    echo "  help      - Mostrar esta ayuda"
    echo ""
    echo "Ejemplos:"
    echo "  ./run.sh start    # Inicia la aplicación"
    echo "  ./run.sh test     # Prueba la función Lambda"
    echo "  ./run.sh logs     # Ver logs en tiempo real"
}

# Función para construir la imagen
build_image() {
    echo "🔨 Construyendo imagen Docker..."
    docker build -t $IMAGE_NAME .
    echo "✅ Imagen construida exitosamente"
}

# Función para verificar si el contenedor está ejecutándose
is_container_running() {
    docker ps --filter "name=$CONTAINER_NAME" --format "{{.Names}}" | grep -q "$CONTAINER_NAME"
}

# Función para verificar si el contenedor existe (pero puede estar parado)
container_exists() {
    docker ps -a --filter "name=$CONTAINER_NAME" --format "{{.Names}}" | grep -q "$CONTAINER_NAME"
}

# Función para iniciar el contenedor
start_container() {
    # Verificar si la imagen existe
    if ! docker images --format "{{.Repository}}" | grep -q "^$IMAGE_NAME$"; then
        echo "⚠️  La imagen no existe. Construyendo..."
        build_image
    fi

    # Detener contenedor existente si está ejecutándose
    if is_container_running; then
        echo "⚠️  Contenedor ya está ejecutándose. Deteniéndolo..."
        docker stop $CONTAINER_NAME
    fi

    # Eliminar contenedor existente si existe
    if container_exists; then
        echo "🗑️  Eliminando contenedor existente..."
        docker rm $CONTAINER_NAME
    fi

    echo "🚀 Iniciando contenedor en puerto $PORT..."
    docker run -d \
        --name $CONTAINER_NAME \
        -p $PORT:8080 \
        $IMAGE_NAME

    echo "✅ Contenedor iniciado exitosamente"
    echo "🌐 Lambda disponible en: http://localhost:$PORT/2015-03-31/functions/function/invocations"
    echo ""
    echo "Para probar la función, ejecuta: ./run.sh test"
}

# Función para detener el contenedor
stop_container() {
    if is_container_running; then
        echo "🛑 Deteniendo contenedor..."
        docker stop $CONTAINER_NAME
        echo "✅ Contenedor detenido"
    else
        echo "⚠️  El contenedor no está ejecutándose"
    fi
}

# Función para ver logs
show_logs() {
    if container_exists; then
        echo "📋 Mostrando logs del contenedor..."
        docker logs -f $CONTAINER_NAME
    else
        echo "❌ El contenedor no existe"
    fi
}

# Función para probar la función Lambda
test_function() {
    if ! is_container_running; then
        echo "❌ El contenedor no está ejecutándose. Iniciando..."
        start_container
        echo "⏳ Esperando que el contenedor esté listo..."
        sleep 3
    fi

    if [ ! -f "payload.json" ]; then
        echo "❌ No se encontró payload.json"
        echo "💡 Asegúrate de que payload.json existe con un PDF en base64"
        return 1
    fi

    echo "🧪 Ejecutando prueba con payload.json..."
    echo "⏳ Esto puede tomar unos segundos..."
    
    curl -X POST \
        "http://localhost:$PORT/2015-03-31/functions/function/invocations" \
        -H "Content-Type: application/json" \
        --data-binary @payload.json \
        --silent \
        --show-error \
        | jq '.' 2>/dev/null || echo "Respuesta recibida (instalar 'jq' para formato JSON)"
        
    echo ""
    echo "✅ Prueba completada"
}

# Función para mostrar estado
show_status() {
    echo "📊 Estado del contenedor:"
    if is_container_running; then
        echo "✅ Contenedor está ejecutándose"
        docker ps --filter "name=$CONTAINER_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    elif container_exists; then
        echo "⚠️  Contenedor existe pero está detenido"
        docker ps -a --filter "name=$CONTAINER_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    else
        echo "❌ Contenedor no existe"
    fi
}

# Función para limpiar
clean_up() {
    echo "🧹 Limpiando contenedor..."
    if is_container_running; then
        docker stop $CONTAINER_NAME
    fi
    if container_exists; then
        docker rm $CONTAINER_NAME
    fi
    echo "✅ Limpieza completada"
}

# Procesar argumentos
case "${1:-start}" in
    "build")
        build_image
        ;;
    "start")
        start_container
        ;;
    "stop")
        stop_container
        ;;
    "restart")
        stop_container
        start_container
        ;;
    "test")
        test_function
        ;;
    "logs")
        show_logs
        ;;
    "status")
        show_status
        ;;
    "clean")
        clean_up
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        echo "❌ Comando desconocido: $1"
        echo ""
        show_help
        exit 1
        ;;
esac