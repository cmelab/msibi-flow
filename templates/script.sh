{% set cmd_prefix = "singularity exec --nv --bind $(pwd) $PLANCKTON_SIMG " %}
{% extends base_script %}
{% block project_header %}
{{ super() }}
export HOOMD_WALLTIME_STOP=$((`date +%s` + {{48|format_timedelta }} * 3600 - 10 * 60))
{% endblock %}
