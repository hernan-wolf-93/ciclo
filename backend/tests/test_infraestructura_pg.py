import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.models import Etapa, Recepcion, Servicio


def test_catalogos_vienen_de_las_migraciones(db_pg):
    etapa = db_pg.scalar(select(Etapa).where(Etapa.orden == 1))
    assert etapa.nombre == "Recepción"
    assert db_pg.scalar(select(func.count()).select_from(Servicio)) > 0


def test_check_de_recepcion_funciona_en_postgres(db_pg):
    servicio = db_pg.scalar(select(Servicio).limit(1))
    with pytest.raises(IntegrityError) as error:
        with db_pg.begin_nested():
            db_pg.add(
                Recepcion(
                    servicio_id=servicio.id,
                    completo=False,
                    servicio_avisado=True,
                    observacion="   ",
                )
            )
            db_pg.flush()
    assert "ck_recepcion_incompleta_requiere_aviso" in str(error.value)


def test_aislamiento_a_escribe_y_confirma(db_pg):
    db_pg.add(Servicio(nombre="Servicio de prueba (aislamiento)"))
    db_pg.commit()


def test_aislamiento_b_no_ve_lo_anterior(db_pg):
    existe = db_pg.scalar(
        select(Servicio).where(Servicio.nombre == "Servicio de prueba (aislamiento)")
    )
    assert existe is None