import wave, os

# Input file parameters (name & location)
input_filename_series = False
input_whole_folder = False
input_filename = 'cut-test.wav'
input_filename_list_range = range(228, 229)
input_filename_list = []
input_path = 'C:\Users\Alex\Google Drive\Ameryn\WTUL\Scripts'
output_path = 'C:\Users\Alex\Google Drive\Ameryn\WTUL\Scripts'

def strip_file(input_filename):

    input_filename_fullpath = os.path.join(input_path, input_filename)
    input_filename = input_filename.split('.wav')[0]

    print 'BLOOOAAARRRRGHHGGGGHHHHH!!! (Please hold...)'
    ifile = wave.open(input_filename_fullpath)
    ifile_params = ifile.getparams()
    ofilename = os.path.join(output_path, input_filename)+'_stripped.wav'

    print input_filename_fullpath,'to', ofilename

    region = wave.open(ofilename, 'w')
    region.setparams(ifile_params)
    # If marker #1 after wave start
    region.writeframes(ifile.readframes(ifile.getnframes()))
    region.close()
    ifile.close()

# Make input filename list
if input_filename_series:
    for f in input_filename_list_range:
        f = str(f).zfill(5)
        for g in os.listdir(input_path):
            if g.startswith(f) and g.endswith('.wav'):
                input_filename_list.append(g)
    print 'Input filenames (series):', input_filename_list

elif input_whole_folder:
    for f in os.listdir(input_path):
        if f.endswith('.wav'):
            input_filename_list.append(f)
    print 'Input filenames (folder):', input_filename_list

else:
    input_filename_list = [input_filename]

# RUN THE TRAP
for each in input_filename_list:
    print each
    strip_file(each)