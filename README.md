AutoTenis

Requisitos

    XAMPP (para activar Apache y MySQL)

    Visual Studio Code

    Python instalado en el sistema 

Pasos de instalación

    Iniciar XAMPP

        Abrir el panel de control de XAMPP.
        Iniciar los servicios de Apache y MySQL.

    Abrir el proyecto en Visual Studio Code

        Abrir la carpeta del proyecto AutoTenis en Visual Studio Code.
        Abrir una nueva terminal (Ctrl + Ñ o desde el menú Terminal > Nueva terminal).

Instalar django y mysqlclient
    Ejecutar en la terminal el comando para instalar django

	-pip install django

    Y luego instalar mysqlclient

	-pip install mysqlclient

Realizar las migraciones
    Ejecutar el siguiente comando para crear los archivos de migración:

        -py manage.py makemigrations

    Luego aplicar las migraciones para crear las tablas en la base de datos:

        -py manage.py migrate

Verificar la creación de la base de datos
Una vez todo instalado ejecutar el siguiente comando:

        -py manage.py runserver

y ya puedes utilizar AutoTenis
